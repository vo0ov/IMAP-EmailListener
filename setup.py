from setuptools import setup, find_packages

setup(
    name='EmailListener',
    version='1.0.0',
    author='Ваше Имя',
    author_email='ваш_email@example.com',
    description='Библиотека для прослушивания и обработки электронных писем через IMAP.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/vo0ov/EmailListener',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'beautifulsoup4>=4.9.3',
    ],
)
