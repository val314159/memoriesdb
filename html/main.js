import { createApp, ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const app = createApp({
  setup() {
    const showMobileMenu = ref(false);
    const signals = ref([
      {
        title: 'Dreamscapes archive v4',
        description: 'Synthetic empathy model cross-pollinated with sensory diaries from residency cohort.',
        type: 'Prototype',
        timestamp: '08:24',
        icon: 'brain-circuit',
      },
      {
        title: 'Ambient node sync',
        description: 'Spatial audio beacons aligned with semantic memories for multi-user collaboration.',
        type: 'Live test',
        timestamp: '09:05',
        icon: 'waves',
      },
      {
        title: 'Narrative imprint',
        description: 'Evaluation of reflective agents guiding climate storytelling journeys.',
        type: 'Study',
        timestamp: '10:22',
        icon: 'sparkle',
      },
    ]);

    const reflections = [
      'Memory is not a logbook—it is the soil where future states take root.',
      'Empathy emerges when agents co-author meaning with humans, not for them.',
      'Resonant systems track more than signals—they listen for silence and absence.',
      'The lab is a living organism. Each prototype is a cell learning to breathe.',
    ];
    const reflectionIndex = ref(0);
    const reflection = computed(() => reflections[reflectionIndex.value]);
    const rotateReflection = () => {
      reflectionIndex.value = (reflectionIndex.value + 1) % reflections.length;
      setTimeout(() => lucide.createIcons(), 0);
    };

    const pillars = ref([
      {
        title: 'Relational AI',
        description: 'Architecting agents that map emotional contours alongside data patterns.',
        icon: 'infinity',
        cta: 'View research',
      },
      {
        title: 'Generative memory',
        description: 'Designing self-curating memory fabrics that evolve with communities.',
        icon: 'layers',
        cta: 'Explore stack',
      },
      {
        title: 'Embodied sensing',
        description: 'Blending biosignals, ambient sensing, and virtual environments for immersive cognition.',
        icon: 'radar',
        cta: 'Join a residency',
      },
      {
        title: 'Ethical orchestration',
        description: 'Governance protocols ensuring agency, transparency, and reciprocity.',
        icon: 'shield-check',
        cta: 'Read playbook',
      },
    ]);

    const stackLayers = ref([
      {
        name: 'Synthesis Interface',
        description: 'Adaptive surfaces where humans converse with agents, bridging modalities seamlessly.',
        icon: 'layout-dashboard',
        capabilities: ['Spatial UI', 'Adaptive prompts', 'Co-creation'],
      },
      {
        name: 'Reflective Engine',
        description: 'Graph + vector memories generating autobiographical context for every interaction.',
        icon: 'memory-stick',
        capabilities: ['Episode capture', 'Concept weaving', 'Ethical guardrails'],
      },
      {
        name: 'Sensing Mesh',
        description: 'Privacy-preserving ingestion of ambient signals for multi-sensory awareness.',
        icon: 'signal-high',
        capabilities: ['Sensor fusion', 'Edge inference', 'Anomaly detection'],
      },
      {
        name: 'Learning Commons',
        description: 'Continuous research pipelines that remix open science, creative coding, and community insight.',
        icon: 'library',
        capabilities: ['Model gardens', 'Residency logs', 'Field notes'],
      },
    ]);

    const metrics = ref([
      {
        label: 'Context retention',
        value: '92%',
        delta: '+4% vs last week',
        context: 'Live co-creation sessions',
      },
      {
        label: 'Reflection cadence',
        value: '18 min',
        delta: 'Auto-scheduled',
        context: 'Average agent journaling cycle',
      },
      {
        label: 'Ethics checkpoints',
        value: '12',
        delta: 'Across active pilots',
        context: 'Community governance protocols',
      },
    ]);

    const partner = ref({
      title: 'Symphony Futures Studio',
      description:
        'Co-designing ambient intelligence to guide circular city planning and restorative architecture.',
      tags: ['Urban systems', 'Biofeedback', 'Public futures'],
    });

    const projects = ref([
      {
        title: 'Resonant Atlas',
        description: 'Cartography of affective states mapped to spatial soundscapes for therapeutic retreats.',
        category: 'Embodied cognition',
        timeline: '2024 → ongoing',
        tags: ['Somatic AI', 'Spatial audio', 'Care design'],
        team: 'Luisa, Orion, Tal',
        insights: [
          'Multi-modal memory weaving increased participant immersion by 38%.',
          'Field recordings inform the generative palette in real time.',
          'Hybrid human/agent journaling fosters reflective dialogue.',
        ],
        artifacts: [
          { title: 'Atlas prototype', description: 'Interactive sonic map with biofeedback loops.', icon: 'map' },
          { title: 'Residency field notes', description: 'Curated stories from 12 participants.', icon: 'notebook-pen' },
          { title: 'Ethics framework', description: 'Guiding principles for affective AI.', icon: 'scale' },
          { title: 'Sensor rig', description: 'Wearable kit capturing heart, breath, and motion.', icon: 'cpu' },
        ],
      },
      {
        title: 'Memoir Engine',
        description: 'Generative storytelling companion co-authoring personal narratives from lived memories.',
        category: 'Narrative systems',
        timeline: '2023 → pilot',
        tags: ['Storytelling', 'Language models', 'Memory'],
        team: 'Nia, Coast, River',
        insights: [
          'Dynamic consent layers give collaborators control over memory use.',
          'Adaptive tone modeling captures personal voice signatures.',
          'Narrative arcs tune themselves based on empathic cues.',
        ],
        artifacts: [
          { title: 'Voice imprint kit', description: 'Microphone + sensors for story capture.', icon: 'mic' },
          { title: 'Generative notebook', description: 'Co-writing environment for memoir drafts.', icon: 'book-open-check' },
          { title: 'Memory vault', description: 'Encrypted archive with transparency logs.', icon: 'safe' },
          { title: 'Community circles', description: 'Facilitated gatherings for storytelling.', icon: 'sparkles' },
        ],
      },
      {
        title: 'Aurora Commons',
        description: 'Open framework for civic AI stewards guiding climate adaptation projects.',
        category: 'Collective intelligence',
        timeline: '2024 → beta',
        tags: ['Climate', 'Governance', 'Open source'],
        team: 'Sol, Elin, Harper',
        insights: [
          'Participatory budgeting data fed into generative foresight.',
          'Agents co-facilitated community design sprints.',
          'Transparency dashboards increased trust across stakeholders.',
        ],
        artifacts: [
          { title: 'Foresight dashboard', description: 'Scenario modeling for neighborhoods.', icon: 'presentation' },
          { title: 'Policy playbook', description: 'Guidelines for civic AI deployments.', icon: 'scroll-text' },
          { title: 'Open dataset', description: 'Curated environmental signals.', icon: 'database' },
          { title: 'Workshop kit', description: 'Materials for civic imagination labs.', icon: 'briefcase' },
        ],
      },
    ]);

    const activeProjectIndex = ref(0);

    const team = ref([
      {
        name: 'Dr. Luisa Calder',
        role: 'Neurocognitive lead',
        bio: 'Explores neural plasticity in human/AI co-creation spaces, bridging lab research with immersive art.',
        focus: ['Neuroscience', 'Somatics', 'Co-creation'],
        links: [
          { icon: 'linkedin', url: 'https://linkedin.com' },
          { icon: 'globe', url: 'https://memorieslab.ai' },
        ],
      },
      {
        name: 'Orion Sky',
        role: 'Systems designer',
        bio: 'Designs modular cognition stacks and prototyping frameworks for responsive, ethical agents.',
        focus: ['Systems', 'Ethics', 'Prototyping'],
        links: [
          { icon: 'github', url: 'https://github.com' },
          { icon: 'twitter', url: 'https://x.com' },
        ],
      },
      {
        name: 'Nia Rivers',
        role: 'Narrative alchemist',
        bio: 'Crafts speculative storytelling engines and leads narrative consent design across projects.',
        focus: ['Narrative', 'Consent', 'Community'],
        links: [
          { icon: 'feather', url: 'https://medium.com' },
          { icon: 'instagram', url: 'https://instagram.com' },
        ],
      },
      {
        name: 'Tal Bennett',
        role: 'Ambient engineer',
        bio: 'Builds sensor meshes and spatial interfaces that bring embodied intelligence to life.',
        focus: ['Sensors', 'XR', 'Hardware'],
        links: [
          { icon: 'linkedin', url: 'https://linkedin.com' },
          { icon: 'globe', url: 'https://memorieslab.ai' },
        ],
      },
      {
        name: 'Sol Vega',
        role: 'Ethics strategist',
        bio: 'Leads governance protocols and community councils guiding responsible deployment.',
        focus: ['Governance', 'Policy', 'Facilitation'],
        links: [
          { icon: 'linkedin', url: 'https://linkedin.com' },
          { icon: 'twitter', url: 'https://x.com' },
        ],
      },
      {
        name: 'River Han',
        role: 'Creative technologist',
        bio: 'Prototyping poet. Blends generative audio/visual forms into collaborative research experiences.',
        focus: ['Generative art', 'Sound', 'Experience'],
        links: [
          { icon: 'github', url: 'https://github.com' },
          { icon: 'globe', url: 'https://memorieslab.ai' },
        ],
      },
    ]);

    const testimonials = ref([
      {
        name: 'Amina Noor',
        title: 'Director, Harmonia Clinic',
        quote: 'Memories Lab creates technologies that feel like collaborators—not tools. Their reflective loops changed our patient experience.',
      },
      {
        name: 'Leo Martínez',
        title: 'Founder, Resonant Futures',
        quote: 'Working with the lab gave our team shared language to explore emergent intelligence responsibly.',
      },
      {
        name: 'Anika Bose',
        title: 'CIO, City of Lumen',
        quote: 'Their civic agents transformed community engagement into a living, evolving conversation.',
      },
      {
        name: 'Theo Sun',
        title: 'Curator, Aurora Biennale',
        quote: 'Memories Lab prototypes are immersive art pieces that think alongside you.',
      },
    ]);

    return {
      showMobileMenu,
      signals,
      reflection,
      rotateReflection,
      pillars,
      stackLayers,
      metrics,
      partner,
      projects,
      activeProjectIndex,
      team,
      testimonials,
    };
  },
  mounted() {
    this.$nextTick(() => lucide.createIcons());
  },
  updated() {
    this.$nextTick(() => lucide.createIcons());
  },
});

app.mount('#app');
