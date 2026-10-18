// {nma-video} and {nma-slides}: static embeds on the website, no kernel.
// nma_kit.media (Python) builds the matching notebook code cells.
// Keep the URL templates in both in sync.

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

const nmaSlides = {
  name: 'nma-slides',
  doc: 'Embedded OSF slide deck with a download link.',
  arg: { type: String, required: true, doc: 'OSF file id, e.g. snv4m.' },
  options: { title: { type: String, doc: 'Heading shown above the slides.' } },
  run(data) {
    const id = data.arg;
    const title = data.options?.title ?? 'Tutorial slides';
    const src = `https://mfr.ca-1.osf.io/render?url=https://osf.io/${id}/?direct%26mode=render%26action=download%26mode=render`;
    return [
      {
        type: 'div',
        class: 'nma-slides',
        children: [
          heading(title),
          iframe(src, title),
          {
            type: 'paragraph',
            children: [link(`https://osf.io/download/${id}/`, 'Download the slides')],
          },
        ],
      },
    ];
  },
};

export default {
  name: 'Neuromatch media',
  directives: [nmaVideo, nmaSlides],
};
