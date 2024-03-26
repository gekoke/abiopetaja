{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    packages = {
      abiopetaja = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
      };

      default = self.packages.${system}.abiopetaja;
    };
  };
}
