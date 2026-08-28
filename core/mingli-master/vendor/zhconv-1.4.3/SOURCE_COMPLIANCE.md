# zhconv 1.4.3 source-compliance procedure

Component: `zhconv==1.4.3`

Current Runtime installation path:

1. `requirements-runtime.lock` pins `zhconv==1.4.3`.
2. `scripts/provision_runtime.py` asks `pip` to install that lock without a
   `zhconv` wheel override.
3. PyPI publishes exactly one artifact for this release: the source archive
   `zhconv-1.4.3.tar.gz`.
4. The source archive contains `LICENSE`, `LICENSE.data`, `setup.py`, all
   shipped Python sources, and `zhconv/zhcdict.json`. Runtime applies no source
   patch.

Official source access:

- Release page: <https://pypi.org/project/zhconv/1.4.3/>
- Exact source archive:
  <https://files.pythonhosted.org/packages/25/47/c8ae2d5d4025e253211ff3d8c163f457db1da94976cb582337a5ab76cb87/zhconv-1.4.3.tar.gz>
- Upstream tag: <https://github.com/gumblex/zhconv/tree/v1.4.3>

For the current provision-from-source path, recipients obtain the complete
unmodified source archive rather than only an object-code copy. If a future
release redistributes a built or installed `zhconv` tree without equivalent
source access, that release remains on HOLD until it accompanies the complete
corresponding source or adopts an approved written-offer process.

This procedure closes source availability for the current installation path.
It does not decide whether the application's in-process import of the
GPLv2+-declared package is compatible with the project's distribution terms.
That compatibility decision remains HOLD.
