{ inputs, ... }:
{
  perSystem = { pkgs, system, ... }: {
    _module.args.pkgs = import inputs.nixpkgs {
      inherit system;
      overlays = [
        inputs.poetry2nix.overlays.default
      ];
    };
  };
}
