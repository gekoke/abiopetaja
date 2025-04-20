{ self, ... }:
{
  flake = {
    nixosModules = {
      abiopetaja = ./services/abiopetaja.nix;
      default = self.nixosModules.abiopetaja;
    };
  };
}
