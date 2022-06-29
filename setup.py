from distutils.core import setup

setup(name='dsapi',
      version='1.0',
      install_requires=['pycryptodome'],
      py_modules=['dsapi', 'define'],
      url='https://github.com/lltcggie/py-dsapi',
      description='dsapi',
      author="lltcggie",
      python_requires=">=3.9"
      )
