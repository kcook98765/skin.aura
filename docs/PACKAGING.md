# Restored original-assets Omega alpha packaging

Source restoration reference: `688290914a31d0f595179043062cc57eb85ab8d9`.
The superseded cleaned source 88e580b remains an ancestor in retained history.
Current inventory is **1,806 files**: all 1,802 original Omega runtime paths plus
four supplemental text notice files. Original resources, all runtime XML and
addon.xml are byte-identical to the reference. Only README, changelog.txt and
THIRD-PARTY-NOTICES.txt differ among original paths, documenting alpha status,
owner evidence and unresolved redistribution restrictions. No asset is cleared.

Run from the full source checkout with Python 3.10+ and required Git history:

```sh
python3 -B tools/build_omega.py --output /tmp/aura-restored-new-build
```

Output must be a new nonsymlink /tmp directory. The exact manifest and its digest
remain pinned; the active exclusion list is empty and hash-pinned. The retired
506-path list and image generator remain in tools/history and original Git
commits, outside the runtime payload. Do not run the retired generator.

The retained builder creates canonical skin.aura-2.1.0.zip with sorted regular
0644 entries, fixed 1980 timestamps, DEFLATE9, CRC/source/stage/readback checks.
Repeated builds must match. Baseline 2.0.23 packaging and its original inventory
are unchanged. Existing published ZIPs/versions must never be rebuilt/replaced.
No 2.1.0 public artifact was admitted; superseded private candidates remain retained.

Original font notices, PDF, flags, photos, screenshots, previews and title art
remain intact. Supplemental Apache/change/iconmonstr/asset notices remain.
Original screenshot dimensions intentionally reproduce five checker errors.
Package consistency supplies no rights or native acceptance. Rights/static
admission remain blocked until legitimately resolved; private candidate feed
qualification may proceed with truthful false/pending acceptance fields.
