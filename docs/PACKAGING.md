# Packaging the Omega alpha

Run from a full source checkout retaining baseline commit
`203aba5117f185a34fef773134d3cf955cbf2c7a`, with Python 3.10+ and Git:

```sh
python3 -B tools/build_omega.py --output /tmp/aura-alpha-new-build
```

Output must be new, outside source, under an existing nonsymlink /tmp parent.
The current candidate is `skin.aura`, name Aura, provider kcook98765, version
2.1.0. No 2.1.0 tag/release or retention-ledger artifact existed at preparation,
so its first public artifact can retain this version. Never replace published
ID/version bytes; later runtime changes need a higher numeric version.

Current exact payload: **1,300 files**. tools/runtime-files.txt pins membership;
tools/runtime-exclusions.txt explicitly records 506 removals from the prior
1,802-file candidate and four added notice files. The historical import anchor
and both file-list digests are checked by omega_common.py. Unexpected additions,
missing files, links, caches, credentials, profiles and generated shortcuts fail.
Do not regenerate the approved list at build time. Notices remain in the payload.

The builder stages 0755 directories and 0644 files, produces canonical
`skin.aura-2.1.0.zip` with sorted regular file entries, fixed 1980 timestamps,
DEFLATE level 9, CRC and source/stage/archive readback checks. Directory entries
were removed from current ZIPs to meet kcook-lab-repo's independent archive audit;
Kodi creates parents. The builder itself performs no validation. Build twice
and compare exact bytes. Retain receipt.json, per-file hashes, Git head/dirty
disposition, tooling hashes and immutable source snapshot outside the package.

A separate `--baseline` build retains original 2.0.23 historical files and ZIP
format/name. Its known failures are not waivers or current acceptance. Do not
publish it or rebuild any old published artifact. Git/source archives are not
the supported installer. docs/, tools/, agent configuration and evidence stay
outside the runtime ZIP; runtime Apache/OFL and iconmonstr terms remain included.

See TESTING.md for lane-matched checks and PUBLICATION.md for uncompleted gates.
The current artifact is local alpha preparation, not approval to publish or a
native install. Authentic screenshots are optional and currently omitted.
