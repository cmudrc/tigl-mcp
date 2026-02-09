FROM condaforge/miniforge3:latest

SHELL ["/bin/bash", "-lc"]

# Install TiGL + deps into a conda env
RUN mamba create -n tigl -y -c conda-forge python=3.11 meshio numpy gmsh python-gmsh \
 && mamba install -n tigl -y -c dlr-sc -c conda-forge dlr-sc::tigl3 dlr-sc::tixi3 \
 && mamba clean -afy

ENV PATH=/opt/conda/envs/tigl/bin:$PATH

WORKDIR /app
COPY . /app

# Install ONLY the tigl-mcp package (this is where pyproject.toml lives)
RUN pip install -e ./tigl-mcp

# Start MCP over stdio (what your client expects)
CMD ["tigl-mcp-server", "--transport", "stdio"]

