# On Apple Silicon (M1/M2/M3): TiGL/TIXI from dlr-sc are only built for linux/amd64.
# Build with:  docker build --platform linux/amd64 -t tigl-mcp:dev .
FROM condaforge/miniforge3:latest

SHELL ["/bin/bash", "-lc"]

# Install TiGL + deps into a conda env
RUN mamba create -n tigl -y -c conda-forge python=3.11 meshio numpy gmsh python-gmsh su2 \
 && mamba install -n tigl -y -c dlr-sc -c conda-forge dlr-sc::tigl3 dlr-sc::tixi3 \
 && mamba clean -afy

ENV PATH=/opt/conda/envs/tigl/bin:$PATH

# Verify SU2 binaries (used for CFD after TiGL export + meshing)
RUN which SU2_CFD && SU2_CFD --help 2>/dev/null || true

WORKDIR /app
COPY . /app

# Install ONLY the tigl-mcp package (this is where pyproject.toml lives)
RUN conda run -n tigl pip install -e .

# Start MCP over stdio (what your client expects)
CMD ["tigl-mcp-server", "--transport", "stdio"]

