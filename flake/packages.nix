{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    packages =
      let
        appDefinition = {
          projectDir = ../.;
          python = pkgs.python312;
          postPatch = ''
            substituteInPlace app/models.py \
              --replace-fail 'pdflatex' '${pkgs.texliveBasic}/bin/pdflatex'
          '';
        };

        build = appDefinition: pkgs.poetry2nix.mkPoetryApplication appDefinition;
      in
      {
        abiopetaja = build appDefinition;

        abiopetaja-dev = build (appDefinition // { groups = [ "dev" ]; });

        default = self.packages.${system}.abiopetaja;
      };
  };
}
