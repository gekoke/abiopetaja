{ inputs, ... }:
{
  perSystem =
    { pkgs, system, ... }:
    {
      _module.args.pkgs = import inputs.nixpkgs {
        inherit system;
        overlays = [
          inputs.poetry2nix.overlays.default
          inputs.deploy-rs.overlays.default
          (_final: prev: {
            deploy-rs = {
              inherit (inputs.nixpkgs.legacyPackages.${system}) deploy-rs;
              lib = prev.deploy-rs.lib;
            };
          })
        ];
      };
    };
}
