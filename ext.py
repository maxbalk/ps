import jinja2.nodes       as j2n
import jinja2.environment as j2e
import jinja2.ext         as j2x
import jinja2.parser      as j2p


class TestExtension(j2x.Extension):
  tags = { "test" }

  def parse(self, parser: j2p.Parser):
    test_name = parser.parse_expression()
    body = parser.parse_statements(
      end_tokens=('name:endtest',),
      drop_needle=True
    )
    return j2n.CallBlock(
      self.call_method("helper", [test_name]),
      [], [],
      body
    )
  def _helper(self, test_name, caller: list[j2n.Node]):
    block_content = caller
    return f"""
      -- Begin Test: {test_name} --\n{block_content}\n-- End Test: {test_name} --
    """
