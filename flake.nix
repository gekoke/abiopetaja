{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
    deploy-rs.url = "github:serokell/deploy-rs";
  };

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      pythonEnv = pkgs.python3.withPackages (
        ps: with ps; [
          django
          django-allauth
          django-cleanup
          transformers
          torch
          accelerate
          pydantic
          openai
        ]
      );
    in
    {
      devShells = {
        x86_64-linux = {
          default = pkgs.mkShell {
            buildInputs = [ pythonEnv ];
          };
        };
      };
    };
}
