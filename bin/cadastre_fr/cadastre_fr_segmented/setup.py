

from distutils.core import setup, Extension

module1 = Extension('cadastre_fr_segmented', sources = ['cadastre_fr_segmented.cpp'])

setup (name="cadastre_fr_segmented", version = "0.2", description="Analysis for segmented building from the French Cadastre.", ext_modules=[module1])

