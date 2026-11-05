import fs from 'node:fs';
import path from 'node:path';

/** The Playwright config sets cwd to the repository root for shared fixtures. */
export function backendPython():string{
 if(process.env.CLIPFORGE_TEST_PYTHON)return process.env.CLIPFORGE_TEST_PYTHON;
 const suffix=process.platform==='win32'?'Scripts/python.exe':'bin/python';
 for(const directory of ['backend/.venv','.venv']){
  const candidate=path.resolve(directory,suffix);
  if(fs.existsSync(candidate))return candidate;
 }
 return process.platform==='win32'?'python':'python3';
}
