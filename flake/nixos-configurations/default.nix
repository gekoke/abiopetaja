{ self, inputs, ... }:
let
  system = "x86_64-linux";
  pkgs = import inputs.nixpkgs { inherit system; };
  mkSystem = inputs.nixpkgs.lib.nixosSystem;
in
{
  flake = {
    nixosConfigurations = {
      ec2 = mkSystem {
        inherit system;
        modules = [
          "${inputs.nixpkgs}/nixos/modules/virtualisation/amazon-image.nix"
          (import ./base-config.nix { inherit self pkgs; })
        ];
      };
    };
  };
}
