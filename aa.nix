{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.texlive.combined.scheme-full
    pkgs.gcc
    pkgs.python3
    pkgs.python3Packages.virtualenv
    pkgs.python3Packages.sentencepiece

  ];
}
