{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    flake-parts.url = "github:hercules-ci/flake-parts";

    # FIXME: delete when https://github.com/nix-community/poetry2nix/pull/1515 is merged
    poetry2nix.url = "github:gekoke/poetry2nix";

    pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";

    deploy-rs.url = "github:serokell/deploy-rs";
  };

  outputs = inputs: import ./flake inputs;
}
