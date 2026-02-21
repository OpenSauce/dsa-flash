import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import yaml from 'highlight.js/lib/languages/yaml'
import 'highlight.js/styles/github.min.css'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('dockerfile', dockerfile)
hljs.registerLanguage('go', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('python', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('yaml', yaml)

let _md: MarkdownIt | null = null

export function useMarkdown(): MarkdownIt {
  if (!_md) {
    _md = new MarkdownIt({
      breaks: true,
      highlight: (str: string, lang: string) => {
        if (lang && hljs.getLanguage(lang)) {
          return (
            `<pre class="hljs"><code class="language-${lang}">` +
            hljs.highlight(str, { language: lang }).value +
            `</code></pre>`
          )
        }
        return `<pre class="hljs"><code>` + hljs.highlightAuto(str).value + `</code></pre>`
      },
    })
      .disable('html_inline')
      .disable('html_block')
  }
  return _md
}
