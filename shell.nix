{ pkgs ? import <nixpkgs> {} }:

# nixpkgs here is an unstable "25.11pre-git" revision, so cache.nixos.org has no
# prebuilt binary for the `caldav` package and it builds from source. Its build
# runs the upstream test suite (checkPhase), which hangs on network I/O in the
# sandbox. We only need the library at runtime, so disable its checks.
let
  python = pkgs.python311.override {
    self = python;
    packageOverrides = final: prev: {
      caldav = prev.caldav.overridePythonAttrs (old: {
        doCheck = false;
        doInstallCheck = false;
        pytestCheckPhase = "true";
        nativeCheckInputs = [ ];
      });
    };
  };
  pyEnv = python.withPackages (ps: with ps; [
    fastapi
    uvicorn
    caldav
    icalendar
    pyyaml
    pydantic
    python-dateutil
    httpx
    pytest
    pytest-asyncio
  ]);
in
pkgs.mkShell {
  buildInputs = [ pyEnv ];
}
