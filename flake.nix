{
  inputs = {
    nixpkgs.url          = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url      = "github:hercules-ci/flake-parts";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
    deploy-rs.url        = "github:serokell/deploy-rs";
  };

  outputs = { nixpkgs, ... }:
  let
    system = "x86_64-linux";
    pkgs   = import nixpkgs { inherit system; };

    texliveWithTikZ = pkgs.texlive.combine {
      inherit (pkgs.texlive) scheme-small collection-pictures;  # pgf ⇒ tikz.sty
    };

    pythonEnv = pkgs.python3.withPackages (ps: with ps; [
      django django-allauth django-cleanup
      transformers torch accelerate
      pydantic openai
    ]);
  in
  {
    ################################################################
    # Correct attribute path: devShells.${system}.default
    ################################################################
    devShells.${system}.default = pkgs.mkShell {
      ################################################################
      # ❶  Make TikZ‑capable TeX Live available in the shell
      ################################################################
      buildInputs = [
        pythonEnv
        texliveWithTikZ           # ← now part of the env
      ];

      ################################################################
      # ❷  (Optional) Force our TeX ahead of /usr/bin in PATH
      ################################################################
      shellHook = ''
        export PATH=${texliveWithTikZ}/bin:$PATH
      '';
    };
  };
}
