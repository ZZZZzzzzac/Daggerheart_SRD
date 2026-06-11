from markdown.extensions.md_in_html import (
    HTMLExtractorExtra, MarkdownInHtmlProcessor, MarkdownInHTMLPostprocessor
)
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension


class SageHTMLExtractor(HTMLExtractorExtra):
    """让 <details> 和 <div class="sage-touched"> 默认启用块级 Markdown 解析"""

    def get_state(self, tag, attrs):
        md_attr = attrs.get('markdown', '0')
        if md_attr == 'markdown':
            md_attr = '1'

        parent_state = self.mdstate[-1] if self.mdstate else None

        if md_attr == '0' and parent_state != 'off':
            if tag == 'div' and attrs.get('class', '') == 'sage-touched':
                md_attr = '1'
            elif tag == 'details':
                md_attr = '1'

        if parent_state == 'off' or (parent_state == 'span' and md_attr != '0'):
            md_attr = parent_state
        if ((md_attr == '1' and tag in self.block_tags) or
                (md_attr == 'block' and tag in self.span_and_blocks_tags)):
            return 'block'
        elif ((md_attr == '1' and tag in self.span_tags) or
              (md_attr == 'span' and tag in self.span_and_blocks_tags)):
            return 'span'
        elif tag in self.block_level_tags:
            return 'off'
        else:
            return None


class SageHtmlPreprocessor(Preprocessor):
    """用 SageHTMLExtractor 替换默认的 HTMLExtractorExtra"""

    def run(self, lines):
        source = '\n'.join(lines)
        parser = SageHTMLExtractor(self.md)
        parser.feed(source)
        parser.close()
        return ''.join(parser.cleandoc).split('\n')


class SageTouchedExtension(Extension):
    """贤者恩泽 Markdown 扩展"""

    def extendMarkdown(self, md):
        md.preprocessors.register(SageHtmlPreprocessor(md), 'html_block', 20)
        md.parser.blockprocessors.register(
            MarkdownInHtmlProcessor(md.parser), 'markdown_block', 105
        )
        md.postprocessors.register(MarkdownInHTMLPostprocessor(md), 'raw_html', 30)


def makeExtension(**kwargs):
    return SageTouchedExtension(**kwargs)
