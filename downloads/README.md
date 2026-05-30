# downloads/

Binaries served by the web container at `/download/`.

Drop the Windows installer here so the landing page's download button works:

```
downloads/CryptTraject-Setup.exe   ->   http://<VPS>/download/CryptTraject-Setup.exe
```

The file is bind-mounted read-only into nginx (see `docker-compose.prod.yml`),
so you can replace it without rebuilding the web image — no restart needed.

The installer itself is produced by the GitHub Actions release workflow
(`.github/workflows/release.yml`) or locally on Windows with
`python packaging/build_binaries.py`. It is **not** committed to git
(see `.gitignore`); copy it onto the VPS, e.g.:

```
scp dist/CryptTraject-Setup.exe root@<VPS>:~/Crypttraject-Software/downloads/
```
