{ self, ... }:
{
  perSystem = { pkgs, system, ... }:
  let
    ############################################################
    # TeX Live that contains pgf ⇒ tikz.sty
    ############################################################
    texliveWithTikZ = pkgs.texlive.combine {
      inherit (pkgs.texlive) scheme-small collection-pictures;
    };

    appDefinition = {
      projectDir = ../.;

      python = pkgs.python312;

      ##########################################################
      # 1.  Point pdf.py at the *new* pdflatex binary
      ##########################################################
      postPatch = ''
        substituteInPlace app/pdf.py \
          --replace-fail 'pdflatex' '${texliveWithTikZ}/bin/pdflatex'
      '';

      ##########################################################
      # 2.  Make the bundle available in PATH for any
      #     subprocess that still calls plain "pdflatex"
      ##########################################################
      buildInputs = [ texliveWithTikZ pkgs.poppler_utils ];

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
    packages = {
      abiopetaja      = build appDefinition;
      abiopetaja-dev  = build (appDefinition // { groups = [ "dev" ]; });
      default         = self.packages.${system}.abiopetaja;
    };
  };
}
