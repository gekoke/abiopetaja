{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    packages = {
      abiopetaja = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
      };

      abiopetaja-tests = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
        groups = ["tests"];
      };

      default = self.packages.${system}.abiopetaja;
    };
  };
}
