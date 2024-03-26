{ self, inputs, ... }:
{
  flake = {
    nixosConfigurations =
      let
        system = "x86_64-linux";
        mkSystem = inputs.nixpkgs.lib.nixosSystem;
      in
      {
        ec2 = mkSystem {
          inherit system;
          specialArgs = { inherit (self.packages.${system}) abiopetaja; };
          modules = [
            "${inputs.nixpkgs}/nixos/modules/virtualisation/amazon-image.nix"
            self.nixosModules.abiopetaja
            {
              system.stateVersion = "24.05";

              services.abiopetaja = {
                enable = true;
                domains = [
                  "xn--abipetaja-s7a.ee"
                  "www.xn--abipetaja-s7a.ee"
                ];
              };
            }
          ];
        };
      };
  };
}
