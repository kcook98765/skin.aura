#!/usr/bin/env python3
"""Exact pre-cleanup Omega/current/superseded source reconciliation; no native calls."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from omega_common import Source, RESTORED_OMEGA_COMMIT, RESTORED_DOCUMENTATION, git

ROOT = Path(__file__).resolve().parents[1]
SUPERSEDED = '88e580b2b42c91b243cf014467e00c1b09944de9'
NOTICE_ADDITIONS = {'fonts/Apache-2.0.txt','fonts/Roboto-Regular-LineSpacingMod-NOTICE.txt',
                    'resources/ICONMONSTR-LICENSE.txt','resources/LEGACY-ASSET-NOTICES.txt'}


def snapshot(ref):
    names = git(ROOT,'show',ref+':tools/runtime-files.txt').decode().splitlines()
    with tarfile.open(fileobj=io.BytesIO(git(ROOT,'archive','--format=tar',ref))) as archive:
        return {n:archive.extractfile(n).read() for n in names}


def compare():
    original=snapshot(RESTORED_OMEGA_COMMIT);old=snapshot(SUPERSEDED);source=Source(ROOT)
    current={n:source.read(n) for n in source.files};removed=sorted(set(original)-set(old))
    changed=sorted(n for n in set(original)&set(old) if original[n]!=old[n])
    graphics=lambda n:Path(n).suffix.lower() in {'.png','.jpg','.jpeg','.ttf','.otf','.xbt'}
    missing=sorted(set(original)-set(current));changed_original=sorted(n for n in set(original)&set(current) if original[n]!=current[n])
    extra=sorted(set(current)-set(original));unexpected=[n for n in changed_original if n not in RESTORED_DOCUMENTATION]
    assert len(original)==1802 and len(old)==1300 and len(current)==1806
    assert len(removed)==506 and len(changed)==19
    assert not missing and not unexpected and set(extra)==NOTICE_ADDITIONS
    assert all(current[n]==original[n] for n in removed)
    replaced=[n for n in changed if graphics(n)]
    assert len(replaced)==12 and all(current[n]==original[n] for n in replaced)
    return {'status':'PASS','pre_cleanup_commit':RESTORED_OMEGA_COMMIT,'superseded_commit':SUPERSEDED,
        'pre_cleanup_file_count':len(original),'superseded_file_count':len(old),'restored_file_count':len(current),
        'formerly_removed_paths':removed,'formerly_changed_common_paths':changed,'formerly_replaced_graphics':replaced,
        'all_formerly_removed_restored_byte_exact':True,'all_replaced_graphics_restored_byte_exact':True,
        'all_original_graphics_fonts_byte_exact':all(current[n]==data for n,data in original.items() if graphics(n)),
        'original_graphics_fonts_count':sum(graphics(n) for n in original),
        'all_original_runtime_except_documentation_byte_exact':not unexpected,
        'original_runtime_paths_byte_exact':len(original)-len(changed_original),
        'all_original_runtime_xml_and_manifest_byte_exact':all(current[n]==data for n,data in original.items() if n.endswith(('.xml','.xsp','.po'))),
        'remaining_changed_original_runtime':changed_original,'added_supplemental_notice_paths':extra,
        'missing_original_paths':missing,'unexpected_visual_functional_deltas':unexpected,
        'appearance_behavior':'Original source resources, presentation XML and manifest preserved exactly; differences limited to release documentation/notices.',
        'installed_production_byte_identity':'unverified; no native inspection or testing',
        'current_runtime_sha256':{n:hashlib.sha256(data).hexdigest() for n,data in sorted(current.items())}}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    report=compare()
    with args.report.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:report[k] for k in ['status','pre_cleanup_file_count','superseded_file_count','restored_file_count','original_graphics_fonts_count','remaining_changed_original_runtime','unexpected_visual_functional_deltas']},indent=2))
