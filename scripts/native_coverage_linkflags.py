Import("env")

# PlatformIO's `build_flags` only reach the compile step for --coverage; the
# link step needs it too so the gcov/profiling runtime gets linked in.
env.Append(LINKFLAGS=["--coverage"])
