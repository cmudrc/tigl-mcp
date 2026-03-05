# On Apple Silicon (M1/M2/M3): TiGL/TIXI from dlr-sc are only built for linux/amd64.
# Build with: docker build --platform linux/amd64 -t tigl-mcp:dev .
FROM condaforge/miniforge3:latest

SHELL ["/bin/bash", "-lc"]

# Install TiGL + geometry and CFD dependencies in a dedicated conda env.
RUN mamba create -n tigl -y -c conda-forge python=3.12 meshio numpy gmsh python-gmsh su2 \
 && mamba install -n tigl -y -c dlr-sc -c conda-forge dlr-sc::tigl3 dlr-sc::tixi3 pythonocc-core \
 && mamba clean -afy

ENV PATH=/opt/conda/envs/tigl/bin:$PATH

# Verify SU2 binaries are present.
RUN which SU2_CFD || (echo "ERROR: SU2_CFD not found" && exit 1)

WORKDIR /app
COPY . /app

# Install package into the TiGL-enabled runtime.
RUN conda run -n tigl pip install -e .

# Start MCP over stdio.
CMD ["tigl-mcp", "--transport", "stdio"]
