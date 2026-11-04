"""Download progress must tolerate yt-dlp moving its temporary fragments."""
import shutil
from pathlib import Path

import pytest
from backend import importer,media


@pytest.mark.parametrize('vanish_at',['before_stat','after_stat'])
def test_fragment_removed_during_progress_does_not_abort_real_video(tmp_path,monkeypatch,vanish_at):
    source=tmp_path/'fixture.mp4'
    media.run(['-f','lavfi','-i','testsrc2=s=160x90:r=10','-t','1','-c:v','libx264',str(source)])
    folder=tmp_path/'download'
    fragment=folder/'source.f616.mp4.part-Frag20'
    url='https://example.com/fixture.mp4'
    original_validate=importer.validate_public_url
    monkeypatch.setattr(importer,'validate_public_url',lambda value:value if value==url else original_validate(value))
    original_stat=Path.stat
    vanished=[]

    def racing_stat(path,*args,**kwargs):
        if path==fragment and not vanished:
            vanished.append(path)
            if vanish_at=='before_stat':
                path.unlink()
                return original_stat(path,*args,**kwargs)
            result=original_stat(path,*args,**kwargs)
            path.unlink()
            # Reproduces deletion between old is_file() and its second stat().
            return result
        return original_stat(path,*args,**kwargs)

    class FragmentedDownload:
        def __init__(self,options):self.options=options
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):
            return {'title':'Actual encoded video','protocol':'m3u8_native','url':url,'duration':1}
        def process_ie_result(self,info,download):
            assert download
            shutil.copyfile(source,folder/'source.mp4')
            fragment.write_bytes(b'temporary fragment')
            monkeypatch.setattr(Path,'stat',racing_stat)
            for hook in self.options['progress_hooks']:
                hook({'status':'finished','downloaded_bytes':source.stat().st_size,'total_bytes':source.stat().st_size})
            return info

    monkeypatch.setattr(importer,'PublicYoutubeDL',FragmentedDownload)
    progress=[]
    result=importer.download_video(url,folder,lambda *args:progress.append(args),max_height=1080)
    assert vanished==[fragment]
    assert not fragment.exists()
    assert result['path']==folder/'source.mp4'
    assert media.probe(result['path'])['duration']==pytest.approx(1,abs=.1)
    assert any(event[2].startswith('Downloading') for event in progress)


def test_size_scan_still_counts_files_and_rejects_oversize_download(tmp_path,monkeypatch):
    folder=tmp_path/'download';folder.mkdir()
    (folder/'source.mp4.part').write_bytes(b'x'*12)
    (folder/'fragment.part').write_bytes(b'x'*8)
    (folder/'cache').mkdir()
    assert importer.download_folder_bytes(folder)==20
    monkeypatch.setattr(importer,'MAX_BYTES',19)
    url='https://example.com/fixture.mp4'
    monkeypatch.setattr(importer,'validate_public_url',lambda value:value)
    class OversizeDownload:
        def __init__(self,options):self.options=options
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):return {'url':url,'protocol':'https'}
        def process_ie_result(self,*args,**kwargs):
            self.options['progress_hooks'][0]({'status':'downloading','downloaded_bytes':1})
    monkeypatch.setattr(importer,'PublicYoutubeDL',OversizeDownload)
    with pytest.raises(ValueError,match='2 GB'):
        importer.download_video(url,folder,lambda *args:None)


def test_size_scan_does_not_hide_other_disk_failures(tmp_path,monkeypatch):
    target=tmp_path/'locked.part';target.write_bytes(b'file')
    original=Path.stat
    def denied(path,*args,**kwargs):
        if path==target:raise PermissionError('Unable to inspect download directory')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'stat',denied)
    with pytest.raises(PermissionError):importer.download_folder_bytes(tmp_path)


def test_missing_fragment_message_explains_local_failure_without_exposing_path():
    message=importer.clean_error("Unable to download video: [WinError 2] The system cannot find the file specified: 'D:\\private\\source.f616.mp4.part-Frag20'")
    assert 'temporary download fragment' in message
    assert 'Retry importing the same link' in message
    assert 'not evidence that the video is private' in message
    assert 'D:' not in message and 'DRM' not in message
