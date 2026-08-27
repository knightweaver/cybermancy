-- Cybermancy Step 6 long-form prose Pandoc filter v1.0
-- Converts normalized prose blocks into the accepted LuaLaTeX publication grammar.

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

function Header(el)
  local tex = inline_latex(el.content)
  if el.level == 3 then
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

function BlockQuote(el)
  -- The accepted grammar makes quotation prose italic regardless of whether
  -- the source already wrapped it in Markdown emphasis. Strip source Emph
  -- wrappers here so \itshape does not toggle them back to roman.
  local wrapper = pandoc.Div(el.content)
  wrapper = wrapper:walk({Emph = function(e) return e.content end})
  el.content = wrapper.content
  if #el.content > 0 then
    local last = el.content[#el.content]
    if last.t == 'Para' or last.t == 'Plain' then
      local first = last.content[1]
      local first_text = (first and first.t == 'Str') and first.text or ''
      if first_text == '--' or first_text == '–' or first_text == '—' then
        table.insert(last.content, 1, pandoc.RawInline('latex', '\\normalfont{}'))
      end
    end
  end
  local blocks = {pandoc.RawBlock('latex', '\\begin{CMQuote}')}
  for _, b in ipairs(el.content) do table.insert(blocks, b) end
  table.insert(blocks, pandoc.RawBlock('latex', '\\end{CMQuote}'))
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
    pandoc.RawBlock('latex', '\\end{multicols}\n\\begin{CMProseTable}'),
    el,
    pandoc.RawBlock('latex', '\\end{CMProseTable}\n\\begin{multicols}{2}')
  }
end

function RawBlock(el)
  if el.format == 'html' then
    local t = el.text or ''
    -- Known MkDocs-only wrappers carry no publication semantics.
    if t:match('^%s*</?div[%s>]') then
      return {}
    end
  end
  return el
end
