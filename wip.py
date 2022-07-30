import site

site.addsitedir(r"D:\Code\Git\_venvs\debugpy\Lib\site-packages")

import debugpy

# debugpy.configure(subProcess=False)
debugpy.listen(("localhost", 5678))
debugpy.wait_for_client()