import os
import PyInstaller.__main__
import git

if __name__ == '__main__':
    # Deletes current version.txt file
    if os.path.exists('version.txt'):
        os.remove('version.txt')

    # Writes latest git version info to 'version.txt'
    r = git.repo.Repo(search_parent_directories=True)
    version_info = r.git.describe('--dirty', '--tags')
    with open('version.txt', 'w') as f:
        f.write(version_info)
        f.write('\n')
        f.close()

    # Builds production version (no debug console window)
    PyInstaller.__main__.run([
        'main.spec'
    ])  