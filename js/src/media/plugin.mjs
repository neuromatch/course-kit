// {nma-video} and {nma-slides}: static embeds on the website, no kernel.
// nma_kit.media (Python) builds the matching notebook code cells.
// Keep the URL templates in both in sync.

import { courseSettings, notebookDir, pageLocation } from '../shared/paths.mjs';
import { osfSlidesEmbedUrl, slideUrl } from './model.mjs';

const VIDEO_SOURCES = [
  {
    option: 'youtube',
    label: 'YouTube',
    embed: (id) => `https://www.youtube.com/embed/${id}?rel=0`,
    page: (id) => `https://youtube.com/watch?v=${id}`,
  },
  {
    option: 'bilibili',
    label: 'Bilibili',
    embed: (id) => `https://player.bilibili.com/player.html?bvid=${id}&page=1&autoplay=0`,
    page: (id) => `https://www.bilibili.com/video/${id}`,
  },
  {
    option: 'osf',
    label: 'OSF',
    embed: (id) =>
      `https://mfr.ca-1.osf.io/render?url=https://osf.io/download/${id}/?direct%26mode=render`,
    page: (id) => `https://osf.io/${id}`,
  },
];

const text = (value) => ({ type: 'text', value });
const link = (url, label) => ({ type: 'link', url, children: [text(label ?? url)] });
const iframe = (src, title) => ({ type: 'iframe', src, width: '100%', title });
const heading = (title) => ({
  type: 'paragraph',
  children: [{ type: 'strong', children: [text(title)] }],
});

function fail(vfile, node, message) {
  const msg = vfile.message(message, node, 'nma-plugin');
  msg.fatal = true;
  return [];
}

const nmaVideo = {
  name: 'nma-video',
  doc: 'Lecture video with one tab per host (YouTube, Bilibili, OSF).',
  arg: { type: String, required: true, doc: 'Video title, e.g. "Video 1: Intro".' },
  options: {
    youtube: { type: String, doc: 'YouTube video id.' },
    bilibili: { type: String, doc: 'Bilibili BV id.' },
    osf: { type: String, doc: 'OSF file id.' },
  },
  run(data, vfile) {
    const sources = VIDEO_SOURCES.filter((s) => data.options?.[s.option]).map((s) => ({
      ...s,
      id: data.options[s.option],
    }));
    if (sources.length === 0) {
      return fail(vfile, data.node, 'nma-video needs at least one of :youtube:, :bilibili:, :osf:');
    }
    const player =
      sources.length === 1
        ? iframe(sources[0].embed(sources[0].id), data.arg)
        : {
            type: 'tabSet',
            children: sources.map((s) => ({
              type: 'tabItem',
              title: s.label,
              children: [iframe(s.embed(s.id), `${data.arg} (${s.label})`)],
            })),
          };
    const links = sources.map((s) => ({
      type: 'paragraph',
      children: [text('Video available at '), link(s.page(s.id))],
    }));
    return [{ type: 'div', class: 'nma-video', children: [heading(data.arg), player, ...links] }];
  },
};

// (option name, tab label), in display order. Python twin: SLIDE_SOURCES in media.py.
const SLIDE_SOURCES = [
  {
    option: 'osf',
    label: 'OSF',
    embed: (id) => osfSlidesEmbedUrl(id),
    download: (id) => `https://osf.io/download/${id}/`,
  },
  {
    option: 'path',
    label: 'PDF',
    embed: (path, url) => url(path),
    download: (path, url) => url(path),
  },
];

/** path -> published URL of a slide PDF for the page at `filePath`, or null when it can't be worked out. */
function slidePathUrl(filePath) {
  const { githubRepo, notebooksBranch } = courseSettings();
  const location = pageLocation(filePath ?? '');
  if (!githubRepo || !location) return null;
  return (path) => slideUrl(githubRepo, notebooksBranch, notebookDir(location), path);
}

const nmaSlides = {
  name: 'nma-slides',
  doc: 'Slide deck with one tab per backend (OSF file, PDF in the course repo) and a download link.',
  arg: { type: String, doc: 'Heading shown above the slides (default: "Tutorial slides").' },
  options: {
    osf: { type: String, doc: 'OSF file id, e.g. snv4m.' },
    path: { type: String, doc: 'PDF in the day folder, e.g. slides/intro.pdf.' },
  },
  run(data, vfile) {
    const title = data.arg || 'Tutorial slides';
    const wanted = SLIDE_SOURCES.filter((s) => data.options?.[s.option]);
    if (wanted.length === 0) {
      return fail(vfile, data.node, 'nma-slides needs at least one of :osf:, :path:');
    }
    const url = slidePathUrl(vfile.path);
    if (data.options?.path && !url) {
      return fail(
        vfile,
        data.node,
        'nma-slides :path: needs project.github in myst.yml and a page inside the tutorials or projects folder',
      );
    }
    const sources = wanted.map((s) => {
      const value = data.options[s.option];
      return { ...s, embedUrl: s.embed(value, url), downloadUrl: s.download(value, url) };
    });
    const player =
      sources.length === 1
        ? iframe(sources[0].embedUrl, title)
        : {
            type: 'tabSet',
            children: sources.map((s) => ({
              type: 'tabItem',
              title: s.label,
              children: [iframe(s.embedUrl, `${title} (${s.label})`)],
            })),
          };
    const links = sources.map((s) => ({
      type: 'paragraph',
      children: [link(s.downloadUrl, sources.length === 1 ? 'Download the slides' : `Download the slides (${s.label})`)],
    }));
    return [{ type: 'div', class: 'nma-slides', children: [heading(title), player, ...links] }];
  },
};

/** The media plugin: the `{nma-video}` and `{nma-slides}` directives. */
export default {
  name: 'Neuromatch media',
  directives: [nmaVideo, nmaSlides],
};
