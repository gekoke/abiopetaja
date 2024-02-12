{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    # FIXME: delete when https://github.com/nix-community/poetry2nix/pull/1515 is merged
    poetry2nix.url = "github:gekoke/poetry2nix";
  };

  outputs = inputs: import ./flake inputs;
}
