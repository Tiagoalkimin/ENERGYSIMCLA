"""O Streamlit sanitiza st.html com DOMPurify, que descarta <script> cujo texto
contenha algo parecido com uma tag (por exemplo "<svg"). Este teste impede que os
scripts de animação voltem a ter marcações literais."""
import re
import unittest

from ui import demo


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_have_no_literal_tags(self):
        for name in ("_CHART_JS", "_COUNT_JS"):
            body = getattr(demo, name).split("<script>")[1].split("</script>")[0]
            self.assertEqual(re.findall(r"<[/\w!]", body), [], name)


if __name__ == "__main__":
    unittest.main()
