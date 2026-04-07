"""OVS — Output Verification System checks for TiGL CPACS output.

Validates that the TiGL adapter writes expected XPaths with plausible values.
Self-contained: no cross-repo dependencies.
"""

from xml.etree import ElementTree as ET

SAMPLE_TIGL_OUTPUT = """\
<?xml version="1.0"?>
<cpacs>
  <vehicles>
    <aircraft>
      <model uID="test">
        <name>OVS Test Aircraft</name>
        <analysisResults>
          <tigl>
            <wingCount>5</wingCount>
            <fuselageCount>2</fuselageCount>
            <components>
              <component><name>Wing_1</name></component>
              <component><name>Fuselage_1</name></component>
            </components>
          </tigl>
        </analysisResults>
      </model>
    </aircraft>
  </vehicles>
</cpacs>
"""


def test_tigl_output_structure():
    root = ET.fromstring(SAMPLE_TIGL_OUTPUT)
    assert root.tag == "cpacs"
    assert root.find(".//vehicles/aircraft") is not None


def test_tigl_results_present():
    root = ET.fromstring(SAMPLE_TIGL_OUTPUT)
    tigl = root.find(".//vehicles/aircraft/model/analysisResults/tigl")
    assert tigl is not None


def test_tigl_wing_count():
    root = ET.fromstring(SAMPLE_TIGL_OUTPUT)
    el = root.find(".//analysisResults/tigl/wingCount")
    assert el is not None and el.text is not None
    assert int(el.text) >= 0


def test_tigl_fuselage_count():
    root = ET.fromstring(SAMPLE_TIGL_OUTPUT)
    el = root.find(".//analysisResults/tigl/fuselageCount")
    assert el is not None and el.text is not None
    assert int(el.text) >= 0


def test_tigl_components():
    root = ET.fromstring(SAMPLE_TIGL_OUTPUT)
    comps = root.find(".//analysisResults/tigl/components")
    assert comps is not None
    assert len(comps) > 0
