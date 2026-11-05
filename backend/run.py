"""Run the Python service and setup commands from the backend directory."""
import argparse
import os
from pathlib import Path
import runpy
import sys

SERVICE = Path(__file__).resolve().parent
REPOSITORY = SERVICE.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='serve', choices=[
        'serve', 'test', 'setup-translation', 'setup-dubbing', 'setup-fonts', 'verify-whisper'])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    options, remaining = parser.parse_known_args(argv)
    os.chdir(REPOSITORY)
    # Keep the service package importable without letting sibling filenames
    # shadow Python standard-library modules when invoked from backend/.
    sys.path[:] = [str(REPOSITORY), *(p for p in sys.path if Path(p or REPOSITORY).resolve() != SERVICE)]
    if (SERVICE/'.env').is_file():
        from dotenv import load_dotenv
        load_dotenv(SERVICE/'.env', override=False)
    if options.command == 'serve':
        if remaining:
            parser.error('Unknown server arguments: '+ ' '.join(remaining))
        import uvicorn
        uvicorn.run('backend.main:app', host=options.host, port=options.port, workers=1)
    elif options.command == 'test':
        import pytest
        return pytest.main(['-c', str(SERVICE/'pytest.ini'), str(SERVICE/'tests'), *remaining])
    else:
        module = 'backend.scripts.' + options.command.replace('-', '_')
        sys.argv = [module, *remaining]
        runpy.run_module(module, run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
