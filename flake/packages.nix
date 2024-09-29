{ self, ... }:
{
  perSystem =
    { pkgs, system, ... }:
    {
      packages =
        let
          appDefinition = {
            projectDir = ../.;
            python = pkgs.python312;

            postPatch = ''
              substituteInPlace app/pdf.py \
                --replace-fail 'pdflatex' '${pkgs.texliveBasic}/bin/pdflatex'
            '';

            configurePhase = ''
              python -m django compilemessages
            '';

            nativeCheckInputs = [ pkgs.poppler_utils ];

            checkPhase = ''
              pytest -n auto
              ${pkgs.pyright}/bin/pyright
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
