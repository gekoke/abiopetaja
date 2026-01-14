{ self, ... }:
{
  flake = {
    nixosModules = {
      abiopetaja = import ./services/abiopetaja.nix { inherit self; };
      default = self.nixosModules.abiopetaja;
    };
  };
}
