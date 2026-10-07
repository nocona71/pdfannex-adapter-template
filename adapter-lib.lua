-- Minimal helpers for a pdfannex adapter, so that this directory has no
-- dependency on the rest of the pdfannex repository: JSON, files and SHA-256.
-- (Derived from cli/pdfannex-lib.lua; copy this file with your adapter.)
local M = {}

---------------------------------------------------------------- JSON
local escapes = { ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f',
                  ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }

local function encode_string(s)
  return '"' .. s:gsub('[%c"\\]', function(c)
    return escapes[c] or string.format("\\u%04x", c:byte())
  end) .. '"'
end

local function is_array(t)
  local n = 0
  for _ in pairs(t) do n = n + 1 end
  return n == #t
end

-- Keys are sorted so output is deterministic (lockfile diffs stay small).
local function encode(v, indent, level)
  local t = type(v)
  if t == "string" then return encode_string(v) end
  if t == "number" or t == "boolean" then return tostring(v) end
  if t ~= "table" then error("cannot encode " .. t) end
  local nl, pad, padc, sep = "", "", "", ","
  if indent then
    nl = "\n"
    pad = string.rep(indent, level + 1)
    padc = string.rep(indent, level)
  end
  local parts = {}
  if next(v) == nil then return "[]" end
  if is_array(v) then
    for i, x in ipairs(v) do parts[i] = pad .. encode(x, indent, level + 1) end
    return "[" .. nl .. table.concat(parts, sep .. nl) .. nl .. padc .. "]"
  end
  local keys = {}
  for k in pairs(v) do keys[#keys + 1] = k end
  table.sort(keys)
  local colon = indent and ": " or ":"
  for i, k in ipairs(keys) do
    parts[i] = pad .. encode_string(k) .. colon .. encode(v[k], indent, level + 1)
  end
  return "{" .. nl .. table.concat(parts, sep .. nl) .. nl .. padc .. "}"
end

function M.json_encode(v, pretty)
  return encode(v, pretty and "  " or nil, 0)
end

function M.json_decode(s)
  local pos = 1
  local function fail(msg) error("invalid JSON at byte " .. pos .. ": " .. msg, 0) end
  local function skip() pos = s:find("[^ \t\r\n]", pos) or #s + 1 end
  local value
  local function str()
    local out = {}
    pos = pos + 1
    while true do
      local c = s:sub(pos, pos)
      if c == "" then fail("unterminated string") end
      if c == '"' then pos = pos + 1; return table.concat(out) end
      if c == "\\" then
        local e = s:sub(pos + 1, pos + 1)
        local map = { b = "\b", f = "\f", n = "\n", r = "\r", t = "\t",
                      ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
        if e == "u" then
          local hex = s:match("^%x%x%x%x", pos + 2) or fail("bad \\u escape")
          out[#out + 1] = utf8.char(tonumber(hex, 16))
          pos = pos + 6
        elseif map[e] then
          out[#out + 1] = map[e]; pos = pos + 2
        else fail("bad escape") end
      else
        out[#out + 1] = c; pos = pos + 1
      end
    end
  end
  function value()
    skip()
    local c = s:sub(pos, pos)
    if c == "{" then
      local obj = {}
      pos = pos + 1; skip()
      if s:sub(pos, pos) == "}" then pos = pos + 1; return obj end
      while true do
        skip()
        if s:sub(pos, pos) ~= '"' then fail("object key expected") end
        local k = str(); skip()
        if s:sub(pos, pos) ~= ":" then fail("':' expected") end
        pos = pos + 1
        obj[k] = value(); skip()
        local d = s:sub(pos, pos); pos = pos + 1
        if d == "}" then return obj end
        if d ~= "," then fail("',' or '}' expected") end
      end
    elseif c == "[" then
      local arr = {}
      pos = pos + 1; skip()
      if s:sub(pos, pos) == "]" then pos = pos + 1; return arr end
      while true do
        arr[#arr + 1] = value(); skip()
        local d = s:sub(pos, pos); pos = pos + 1
        if d == "]" then return arr end
        if d ~= "," then fail("',' or ']' expected") end
      end
    elseif c == '"' then return str()
    elseif s:find("^true", pos) then pos = pos + 4; return true
    elseif s:find("^false", pos) then pos = pos + 5; return false
    elseif s:find("^null", pos) then pos = pos + 4; return nil
    else
      local num = s:match("^-?%d+%.?%d*[eE]?[+-]?%d*", pos)
      if not num or num == "" then fail("unexpected character") end
      pos = pos + #num
      return tonumber(num)
    end
  end
  local result = value()
  skip()
  if pos <= #s then fail("trailing data") end
  return result
end


function M.read_file(path)
  local f, err = io.open(path, "rb")
  if not f then return nil, err end
  local data = f:read("a")
  f:close()
  return data
end

function M.write_file(path, data)
  local f, err = io.open(path, "wb")
  if not f then return nil, err end
  f:write(data)
  f:close()
  return true
end

-- sha2 is provided by texlua (LuaTeX).
function M.sha256_hex(data)
  return (sha2.digest256(data):gsub(".", function(c)
    return string.format("%02x", c:byte())
  end))
end

return M
