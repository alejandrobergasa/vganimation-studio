import sys, ndspy.rom, collections
rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
print(rom.name, rom.idCode, rom.developerCode, rom.region if hasattr(rom,'region') else '')
print('arm9 ovl', len(rom.loadArm9Overlays()), 'arm7 ovl', len(rom.loadArm7Overlays()))
def walk(f, p=''):
    for n in f.folders: yield from walk(n[1], p+n[0]+'/')
    for n in f.files: yield p+n
files = list(walk(rom.filenames))
print(len(files),'files')
ext = collections.Counter(f.rsplit('.',1)[-1] for f in files)
print(ext)
for f in files:
    d = rom.getFileByName(f); print(f, len(d), d[:4])
