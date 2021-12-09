{
  description = "Python job manager for parallel computing.";


  inputs = {
    utils.url = "github:vale981/hiro-flake-utils";
    nixpkgs.url = "nixpkgs/nixos-unstable";
    binfootprint.url = "github:vale981/binfootprint";
    progression.url = "github:vale981/progression";
  };

  outputs = pythonPackages@{ self, utils, nixpkgs, ... }:
    (utils.lib.poetry2nixWrapper nixpkgs pythonPackages {
      name = "jobmanager";
      poetryArgs = {
        projectDir = ./.;
      };
    });
}
