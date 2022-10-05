import blackd

import pathlib

path = pathlib.Path("backd.txt")
path.write_text(str(blackd))

blackd.patched_main()
