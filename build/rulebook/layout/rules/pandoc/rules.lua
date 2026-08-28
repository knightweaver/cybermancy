-- Cybermancy Step 6 Part II rules Pandoc filter v1.0
-- Extends the accepted prose grammar with the accepted Part II rules layout.
-- It does not infer semantic subtypes from text.

local function esc_tex(s)
  s = tostring(s or '')
  s = s:gsub('\\', '\\textbackslash{}')
  s = s:gsub('([%%#&_$])', '\\%1')
  s = s:gsub('{', '\\{')
  s = s:gsub('}', '\\}')
  s = s:gsub('~', '\\textasciitilde{}')
  s = s:gsub('%^', '\\textasciicircum{}')
  return s
end

local function inline_latex(inlines)
  local doc = pandoc.Pandoc({pandoc.Plain(inlines)})
  local s = pandoc.write(doc, 'latex')
  s = s:gsub('%s+$', '')
  return s
end

local function image_meta(img)
  local attrs = img.attributes or {}
  return {
    role = attrs['data-role'] or 'standard',
    missing = attrs['data-missing'] == 'true',
    original = attrs['data-original'] or img.src or '',
    src = img.src or '',
  }
end

-- Each chapter fragment is converted by its own Pandoc process. Step 4 shifts
-- the authored document-root H1 to normalized H3, while Step 6 already renders
-- the authoritative publication title in CMChapterBanner. Suppress only that
-- first H3 in the fragment; later H3 headings remain visible section headings.
local root_h3_suppressed = false

function Header(el)
  local tex = inline_latex(el.content)
  if el.level == 3 then
    if not root_h3_suppressed then
      root_h3_suppressed = true
      return {}
    end
    return pandoc.RawBlock('latex', '\\CMHThree{' .. tex .. '}')
  elseif el.level == 4 then
    return pandoc.RawBlock('latex', '\\CMHFour{' .. tex .. '}')
  elseif el.level == 5 then
    return pandoc.RawBlock('latex', '\\CMHFive{' .. tex .. '}')
  end
  return el
end

function HorizontalRule(el)
  return pandoc.RawBlock('latex', '\\CMSectionRule')
end

-- Noto Serif does not reliably provide the directional-arrow glyphs used by
-- normalized rules text on every LuaLaTeX installation. Preserve the authored
-- character semantically while emitting deterministic TeX math arrows.
function Str(el)
  local text = el.text or ''
  if not (text:find('→', 1, true) or text:find('←', 1, true) or text:find('↔', 1, true)) then
    return el
  end
  local tex = esc_tex(text)
  tex = tex:gsub('→', '\\ensuremath{\\rightarrow}')
  tex = tex:gsub('←', '\\ensuremath{\\leftarrow}')
  tex = tex:gsub('↔', '\\ensuremath{\\leftrightarrow}')
  return pandoc.RawInline('latex', tex)
end

function BlockQuote(el)
  local blocks = {pandoc.RawBlock('latex', '\\begin{CMRulesQuote}')}
  for _, b in ipairs(el.content) do table.insert(blocks, b) end
  table.insert(blocks, pandoc.RawBlock('latex', '\\end{CMRulesQuote}'))
  return blocks
end

function Para(el)
  if #el.content == 1 and el.content[1].t == 'Image' then
    local img = el.content[1]
    local m = image_meta(img)
    local filename = m.original:match('([^/\\]+)$') or m.original
    if m.missing then
      local macro = '\\CMAssetPlaceholder'
      if m.role == 'wide' then macro = '\\CMWideAssetPlaceholder' end
      return pandoc.RawBlock('latex', macro .. '{' .. esc_tex(filename) .. '}')
    end

    local path = m.src:gsub('\\', '/')
    local detok = '\\detokenize{' .. path .. '}'
    if m.role == 'wide' then
      return pandoc.RawBlock('latex', '\\end{multicols}\n\\CMWideImage{' .. detok .. '}\n\\begin{multicols}{2}')
    elseif m.role == 'mark' then
      return pandoc.RawBlock('latex', '\\CMMarkImage{' .. detok .. '}')
    elseif m.role == 'symbolic' then
      return pandoc.RawBlock('latex', '\\CMSymbolicImage{' .. detok .. '}')
    elseif m.role == 'portrait' then
      return pandoc.RawBlock('latex', '\\CMPortraitImage{' .. detok .. '}')
    else
      return pandoc.RawBlock('latex', '\\CMStandardImage{' .. detok .. '}')
    end
  end
  return el
end

function Table(el)
  return {
    pandoc.RawBlock('latex', '\\end{multicols}\n\\begin{CMRulesTable}'),
    el,
    pandoc.RawBlock('latex', '\\end{CMRulesTable}\n\\begin{multicols}{2}')
  }
end

function RawBlock(el)
  if el.format == 'html' then
    local t = el.text or ''
    if t:match('^%s*</?div[%s>]') then
      return {}
    end
  end
  return el
end
