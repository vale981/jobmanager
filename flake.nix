{
  description = "Python job manager for parallel computing.";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-unstable";
    mach-nix.url = "github:DavHau/mach-nix";
    flake-utils.url = "github:numtide/flake-utils";
    binfootprint.url = "github:vale981/binfootprint";
    progression.url = "github:vale981/progression";
  };

   outputs = { self, nixpkgs, flake-utils, mach-nix, binfootprint, progression }:
     let
       python = "python39";

     in flake-utils.lib.eachSystem ["x86_64-linux"] (system:
       let
         pkgs = nixpkgs.legacyPackages.${system};
         mach-nix-wrapper = import mach-nix { inherit pkgs python;  };

         jobmanager = (mach-nix-wrapper.buildPythonPackage {
           src = ./.;
           propagatedBuildInputs = [
             binfootprint.defaultPackage.${system}
             progression.defaultPackage.${system}
           ];
         });

         pythonShell = mach-nix-wrapper.mkPython {
           packagesExtra = [jobmanager];
         };

       in {
         devShell = pkgs.mkShell {
           buildInputs = with pkgs; [pythonShell black pyright];
         };

         defaultPackage = jobmanager;
       });
}
