import palette from "../../backend/src/gittoken/templates/palette.json";
import type { GithubLogin } from "./login";
import { agentsPath, profilePath, userPath } from "./paths";

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;
// Leaves room for the percent beside the bar in the narrowest small widget (141pt), as stacks take sizes in points.
const barTrackWidthPoints = 64;

/** Post: a Scriptable (https://docs.scriptable.app) script that draws login's tokens, rarity and top agents from the /v1/users and /v1/agents routes. */
export function scriptableWidgetScript(
  origin: string,
  login: GithubLogin,
): string {
  return `/* GitToken widget for ${login}. Paste into a new Scriptable script, then add a Scriptable widget that runs it. */
const palette = ${JSON.stringify(palette)};
const widget = new ListWidget();
widget.url = ${JSON.stringify(`${origin}${profilePath(login)}`)};
widget.setPadding(0, 0, 0, 0);
const rim = widget.addStack();
rim.setPadding(2, 2, 2, 2);
const card = rim.addStack();
card.cornerRadius = 20;
card.backgroundColor = themed((theme) => theme.background);
const content = card.addStack();
content.layoutVertically();
content.setPadding(12, 12, 12, 12);

/* Mirrors badge.svg.jinja and card.jinja in backend/src/gittoken/templates. Scriptable gradients cannot follow light
   and dark mode, so each gradient is a theme-neutral overlay on a Color.dynamic base. */
function themed(pick, alpha = 1) {
  return Color.dynamic(new Color(pick(palette.palettes.light), alpha), new Color(pick(palette.palettes.dark), alpha));
}

function themeNeutralHex(pick) {
  const hex = pick(palette.palettes.light);
  if (hex !== pick(palette.palettes.dark)) {
    throw new Error("palette.json: " + hex + " must be the same in both themes for a widget gradient");
  }
  return hex;
}

function mixHex(baseHex, overHex, overAlpha) {
  const channel = (hex, index) => parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16);
  return "#" + [0, 1, 2].map((index) => Math.round(channel(baseHex, index) * (1 - overAlpha) + channel(overHex, index) * overAlpha).toString(16).padStart(2, "0")).join("");
}

function gradient(colors, locations, endPoint) {
  const linearGradient = new LinearGradient();
  linearGradient.colors = colors;
  linearGradient.locations = locations;
  linearGradient.startPoint = new Point(0, 0);
  linearGradient.endPoint = endPoint;
  return linearGradient;
}

/* The middle stop is exact per theme; the end stops fade out of it and use one color for both themes. */
function drawRim(startHex, middleHex, endHex) {
  widget.backgroundColor = themed((theme) => mixHex(theme.background, middleHex, 0.5));
  rim.backgroundGradient = gradient(
    [new Color(startHex, 1), new Color(startHex, 0), new Color(endHex, 0), new Color(endHex, 1)],
    [0, 0.5, 0.5, 1],
    new Point(1, 1),
  );
}

function addText(stack, text, font, color) {
  const widgetText = stack.addText(text);
  widgetText.font = font;
  widgetText.textColor = color;
  widgetText.minimumScaleFactor = 0.5;
  widgetText.lineLimit = 1;
}

function addLine(stack, text, font, color) {
  const line = stack.addStack();
  line.centerAlignContent();
  addText(line, text, font, color);
  line.addSpacer();
  return line;
}

/* A start color fading out over a dynamic end color draws the same blend as the badge's two-stop bar gradient. */
function addBar(stack, fillWidthPoints, startHex, endColor) {
  const track = stack.addStack();
  track.size = new Size(${barTrackWidthPoints}, 4);
  track.cornerRadius = 2;
  track.backgroundColor = themed((theme) => theme.ink, 0.1);
  /* Scriptable sizes a stack automatically when a dimension is 0. */
  if (fillWidthPoints > 0) {
    const fill = track.addStack();
    fill.size = new Size(fillWidthPoints, 4);
    fill.cornerRadius = 2;
    fill.backgroundColor = endColor;
    const fillStart = fill.addStack();
    fillStart.size = new Size(fillWidthPoints, 4);
    fillStart.backgroundGradient = gradient([new Color(startHex, 1), new Color(startHex, 0)], [0, 1], new Point(1, 0));
  }
  track.addSpacer();
}

/* Python's round() and format() round exact halves to even; JavaScript rounds them up. */
function roundHalfEven(value) {
  const floor = Math.floor(value);
  const fraction = value - floor;
  return fraction > 0.5 || (fraction === 0.5 && floor % 2 === 1) ? floor + 1 : floor;
}

/* Matches _format_tokens in backend/src/gittoken/badge.py. */
function formatTokens(tokens) {
  for (const [threshold, suffix] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]]) {
    if (tokens >= threshold) {
      const quotient = tokens / threshold;
      const isTie = Number.isInteger(quotient * 4) && !Number.isInteger(quotient * 2);
      const text = isTie ? (roundHalfEven(quotient * 10) / 10).toFixed(1) : quotient.toFixed(1);
      return text.replace(/\\.0$/, "") + suffix;
    }
  }
  return String(tokens);
}

/* Matches _rows and _MAX_ROWS in backend/src/gittoken/badge.py: tokens_by_agent comes largest first. */
function agentRows(profile, nameByAgent) {
  const row = (name, tokens) => ({
    name,
    tokens,
    percent: roundHalfEven((profile.total_tokens ? tokens / profile.total_tokens : 0) * 100),
  });
  const rows = Object.entries(profile.tokens_by_agent).map(([agent, tokens]) => row(nameByAgent[agent], tokens));
  if (rows.length > 2) {
    return [rows[0], row("Others", rows.slice(1).reduce((sum, other) => sum + other.tokens, 0))];
  }
  return rows;
}

function refreshAfterMinutes(minutes) {
  widget.refreshAfterDate = new Date(Date.now() + minutes * 60 * 1000);
}

async function loadResponse(url) {
  const request = new Request(url);
  const body = await request.load();
  return { statusCode: request.response.statusCode, body };
}

function drawNotice(message) {
  drawRim(...palette.brand_rim_colors);
  addLine(content, ${JSON.stringify(login)}, Font.boldSystemFont(14), themed((theme) => theme.ink));
  content.addSpacer(4);
  addLine(content, message, Font.systemFont(11), themed((theme) => theme.ink, 0.62));
  content.addSpacer();
  refreshAfterMinutes(${errorRefreshMinutes});
}

function drawProfile(user, agents) {
  if (user.statusCode === 200 && agents.statusCode === 200) {
    const profile = JSON.parse(user.body.toRawString());
    const nameByAgent = Object.fromEntries(JSON.parse(agents.body.toRawString()).map(({ agent, name }) => [agent, name]));
    const rarityColors = (theme) => theme.rarities[profile.rarity];
    const accent = themed((theme) => rarityColors(theme)[0]);
    const tintHex = themeNeutralHex((theme) => rarityColors(theme)[2]);
    /* The rim ends differ by theme and no gradient can follow appearance, so both themes use the light ends. */
    const [, rimStartHex, , rimEndHex] = rarityColors(palette.palettes.light);
    drawRim(rimStartHex, tintHex, rimEndHex);
    content.backgroundGradient = gradient([new Color(tintHex, 0.22), new Color(tintHex, 0), new Color(tintHex, 0)], [0, 0.7, 1], new Point(0, 1));
    addLine(content, profile.login, Font.boldSystemFont(14), themed((theme) => theme.ink));
    addLine(content, profile.rarity.toUpperCase(), Font.semiboldSystemFont(9), accent);
    addLine(content, formatTokens(profile.total_tokens), Font.boldSystemFont(22), accent);
    content.addSpacer();
    const rows = agentRows(profile, nameByAgent);
    if (rows.length > 0) {
      const panel = content.addStack();
      panel.layoutVertically();
      panel.spacing = 2;
      panel.cornerRadius = 10;
      panel.setPadding(4, 8, 4, 8);
      panel.backgroundColor = themed((theme) => theme.ink, 0.06);
      const valueColor = themed((theme) => theme.ink, 0.85);
      const valueFont = Font.regularMonospacedSystemFont(9);
      for (const row of rows) {
        const nameLine = addLine(panel, row.name, Font.mediumSystemFont(10), themed((theme) => theme.ink));
        addText(nameLine, formatTokens(row.tokens), valueFont, valueColor);
        const barLine = panel.addStack();
        barLine.centerAlignContent();
        const fillWidthPoints = profile.total_tokens ? Math.max(4, Math.round((${barTrackWidthPoints} * row.tokens) / profile.total_tokens)) : 0;
        addBar(barLine, fillWidthPoints, tintHex, themed((theme) => rarityColors(theme)[3]));
        barLine.addSpacer();
        addText(barLine, row.percent + "%", valueFont, valueColor);
      }
    }
    refreshAfterMinutes(${profileRefreshMinutes});
  } else {
    const statusCode = user.statusCode === 200 ? agents.statusCode : user.statusCode;
    drawNotice(user.statusCode === 404 ? "No such GitHub user" : "Couldn't load tokens (HTTP " + statusCode + ")");
  }
}

function drawUnreachable() {
  drawNotice("Couldn't reach GitToken");
}

/* The rejection handler covers only the requests, so a bug in drawProfile still surfaces as an error. */
await Promise.all([
  loadResponse(${JSON.stringify(`${origin}${userPath(login)}`)}),
  loadResponse(${JSON.stringify(`${origin}${agentsPath}`)}),
]).then(([user, agents]) => drawProfile(user, agents), drawUnreachable);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentSmall();
}
Script.complete();
`;
}
