

from distutils.core import setup, Extension

module1 = Extension('fr_cadastre_segmented', sources = ['fr_cadastre_segmented.cpp'])

setup (name="fr_cadastre_segmented", version = "0.2", description="Analysis for segmented building of the French Cadastre.", ext_modules=[module1])

