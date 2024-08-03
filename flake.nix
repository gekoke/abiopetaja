{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    flake-parts.url = "github:hercules-ci/flake-parts";

    poetry2nix.url = "github:nix-community/poetry2nix";

    pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";

    deploy-rs.url = "github:serokell/deploy-rs";
  };

  outputs = inputs: import ./flake inputs;
}
