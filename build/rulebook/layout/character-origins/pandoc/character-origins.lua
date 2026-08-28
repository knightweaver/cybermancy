-- Cybermancy Step 6 Character Origins Pandoc filter v1.0.1 (draft)
-- Consumes only the derived entry annotations produced from Step 4 normalized
-- Chapters 10-11. Long-Form Prose v1.0 supplies the surrounding publication shell.
--
-- Compatibility note: the frozen Prose v1.0 preamble stores the running accent
-- in the TeX macro \CMRunningAccent, while its fancyhdr definition references
-- the literal xcolor name CMRunningAccent. Chapters 10-11 are player material,
-- so this lane defines that xcolor alias locally without modifying the frozen
-- Prose implementation.

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
  return (s:gsub('%s+$', ''))
end

local function blocks_latex(blocks)
  local s = pandoc.write(pandoc.Pandoc(blocks), 'latex')
  return (s:gsub('%s+$', ''))
end

local function has_class(el, wanted)
  for _, value in ipairs(el.classes or {}) do
    if value == wanted then return true end
  end
  return false
end

local function image_meta(img)
  local attrs = img.attributes or {}
  return {
    missing = attrs['data-missing'] == 'true',
    original = attrs['data-original'] or img.src or '',
    src = img.src or '',
  }
end

local function identity_div(el)
  if #el.content < 3 then
    error('cm-origin-identity requires image, H4 heading, and lead paragraph')
  end

  local image_block = el.content[1]
  local heading = el.content[2]
  if image_block.t ~= 'Para' or #image_block.content ~= 1 or image_block.content[1].t ~= 'Image' then
    error('cm-origin-identity first block must be a standalone image paragraph')
  end
  if heading.t ~= 'Header' or heading.level ~= 4 then
    error('cm-origin-identity second block must be an H4 entry heading')
  end

  local img = image_block.content[1]
  local meta = image_meta(img)
  local image_tex
  if meta.missing then
    local filename = meta.original:match('([^/\\]+)$') or meta.original
    image_tex = '\\CMOriginIdentityMissing{' .. esc_tex(filename) .. '}'
  else
    local path = meta.src:gsub('\\', '/')
    image_tex = '\\CMOriginIdentityImage{\\detokenize{' .. path .. '}}'
  end

  local title = inline_latex(heading.content)
  local lead_blocks = {}
  for i = 3, #el.content do table.insert(lead_blocks, el.content[i]) end
  local lead = blocks_latex(lead_blocks)
  return pandoc.RawBlock('latex', '\\CMOriginIdentity{' .. image_tex .. '}{' .. title .. '}{' .. lead .. '}')
end

local function feature_label_div(el)
  local label = pandoc.utils.stringify(el)
  if label == '' then error('cm-origin-feature-label may not be blank') end
  return pandoc.RawBlock('latex', '\\CMOriginFeatureLabel{' .. esc_tex(label) .. '}')
end

local function feature_div(el)
  if #el.content < 2 then
    error('cm-origin-feature requires a name block and rules block')
  end
  local name = pandoc.utils.stringify(el.content[1])
  if name == '' then error('cm-origin-feature name may not be blank') end
  local desc = {}
  for i = 2, #el.content do table.insert(desc, el.content[i]) end
  return pandoc.RawBlock('latex', '\\CMOriginFeature{' .. esc_tex(name) .. '}{' .. blocks_latex(desc) .. '}')
end

local function Div(el)
  if has_class(el, 'cm-origin-identity') then
    return identity_div(el)
  elseif has_class(el, 'cm-origin-feature-label') then
    return feature_label_div(el)
  elseif has_class(el, 'cm-origin-feature') then
    return feature_div(el)
  end
  return nil
end

local function Header(el)
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

local function HorizontalRule(_)
  return pandoc.RawBlock('latex', '\\CMOriginEntryRule')
end

local function BlockQuote(el)
  local wrapper = pandoc.Div(el.content)
  wrapper = wrapper:walk({Emph = function(e) return e.content end})
  return {
    pandoc.RawBlock('latex', '\\begin{CMQuote}'),
    table.unpack(wrapper.content),
    pandoc.RawBlock('latex', '\\end{CMQuote}')
  }
end

local function Para(el)
  if #el.content == 1 and el.content[1].t == 'Image' then
    local img = el.content[1]
    local meta = image_meta(img)
    local filename = meta.original:match('([^/\\]+)$') or meta.original
    if meta.missing then
      return pandoc.RawBlock('latex', '\\CMAssetPlaceholder{' .. esc_tex(filename) .. '}')
    end
    local path = meta.src:gsub('\\', '/')
    return pandoc.RawBlock('latex', '\\CMStandardImage{\\detokenize{' .. path .. '}}')
  end
  return el
end

local function Table(el)
  return {
    pandoc.RawBlock('latex', '\\end{multicols}\n\\begin{CMProseTable}'),
    el,
    pandoc.RawBlock('latex', '\\end{CMProseTable}\n\\begin{multicols}{2}')
  }
end

local function RawBlock(el)
  if el.format == 'html' and (el.text or ''):match('^%s*</?div[%s>]') then
    error('Raw MkDocs div wrapper reached Character Origins Step 6 filter')
  end
  return el
end

local function Pandoc(doc)
  table.insert(
    doc.blocks,
    1,
    pandoc.RawBlock('latex', '\\colorlet{CMRunningAccent}{CMCyan}')
  )
  return doc
end

return {
  {
    traverse = 'topdown',
    Div = Div,
    Header = Header,
    HorizontalRule = HorizontalRule,
    BlockQuote = BlockQuote,
    Para = Para,
    Table = Table,
    RawBlock = RawBlock,
    Pandoc = Pandoc,
  }
}
