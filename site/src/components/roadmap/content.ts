// components/roadmap/content.ts
//
// Data layer typé pour la page roadmap Aratea, pattern Dictionary similaire
// au i18n du dashboard. Source de vérité du contenu — modifier ici pour mettre
// à jour la roadmap publique. Build déterministe, pas de pull runtime.
//
// La version EN sert de schéma de référence pour le type Content.
// La version FR doit satisfaire le même type (vérifié par TypeScript).

import type { ReactNode } from "react";

export type Status = "done" | "in-progress" | "planned";
export type Priority = "P1" | "P2" | "P3";
export type Locale = "fr" | "en";

export interface Phase {
  id: string;
  number: string; // "I", "II", "III", "IV", "V+"
  title: string;
  subtitle?: string;
  status: Status;
  description: ReactNode;
  deliverables: ReactNode[];
}

export interface BacklogItem {
  priority: Priority;
  title: string;
  description: ReactNode;
}

export interface NoteItem {
  title: string;
  body: ReactNode;
}

export type Content = {
  version: string;
  date: string;
  hero: {
    title: string;
    subtitle: string;
    preamble: ReactNode;
    quote: string;
    quoteAttribution: string;
  };
  state: {
    title: string;
    doneLabel: string;
    inProgressLabel: string;
    done: ReactNode[];
    inProgress: ReactNode[];
  };
  phasesTitle: string;
  phases: Phase[];
  backlogTitle: string;
  backlog: BacklogItem[];
  notesTitle: string;
  notes: NoteItem[];
  status: Record<Status, string>;
  priority: Record<Priority, string>;
  footer: ReactNode;
  switchLabel: string;
};

export const en: Content = {
  version: "v0.1",
  date: "May 16, 2026",
  hero: {
    title: "Roadmap",
    subtitle: "Aratea's trajectory, open and versioned.",
    preamble:
      "Public source of truth on the project's state and trajectory. Updated on technical milestones, not on calendar dates. Complements the white paper (FR/EN v0.5) describing the architecture and the model.",
    quote: '"The sky speaks in signs. Each has its season."',
    quoteAttribution:
      "Aratus of Soli, Phaenomena, 3rd century BC — paraphrase.",
  },
  state: {
    title: "State as of May 16, 2026",
    doneLabel: "Done",
    inProgressLabel: "In progress",
    done: [
      "Augure → Aratea rebrand (May 11, 2026). Aratus of Soli etymology documented.",
      "White paper FR + EN v0.5 published on Notion, 13 sections, unified token-weighted governance.",
      "Public repository github.com/Elladriel80/Aratea open and active.",
      "AUG-POC token deployed on Arbitrum Sepolia (testnet).",
      "Initial Phase 1 capital: USD 1,000 of ETH, founder-funded. External subscription closed.",
      "learned_v2 predictor delivered May 12, 2026, promotable-gate infrastructure active.",
      "Discord + automated announce system on Git tags, delivered May 9, 2026.",
      "White-hat security audit, PR #18 merged, history rewrite, Pinata + webhooks + Etherscan rotations.",
      "Competitor benchmark: 7 actors analyzed (Augur, Etherisc, Arbol, Nexus Mutual, UMA, Reclaim, Polymarket).",
      "Bylaws v0 project draft (FR + EN) for-profit Alsace-Moselle association, 40 articles.",
    ],
    inProgress: [
      "Phase 1 Kalshi paper trading — critical path remains beating kalshi_mid on Brier score. Bench of May 11, 2026 on N=138: learned_v2 0.1305 vs kalshi_mid 0.0845.",
      "learned_v2 iteration — named feature engineering with leave-one-out Brier delta measurement.",
      "Code-side migration Augure → Aratea (paths, Discord identifiers, repo slug).",
    ],
  },
  phasesTitle: "Phases",
  phases: [
    {
      id: "phase-1",
      number: "I",
      title: "Edge validation",
      subtitle: "Current — Kalshi paper trading",
      status: "in-progress",
      description:
        "The learned predictor must beat kalshi_mid on Brier score over an independent test set of N > 50 fresh events. Honest criterion, written before the result. Without it, the project pivots scope or shuts down cleanly.",
      deliverables: [
        "Feature engineering iteration until threshold cleared or feature ideas exhausted.",
        "Reclaim Protocol technical POC — a few hours on an NWS station.",
        "Paper → live switch once edge is materialized on N > 50.",
        '"Why Aratea and not Etherisc" section in the white paper.',
      ],
    },
    {
      id: "phase-2",
      number: "II",
      title: "DAO MVP testnet",
      subtitle: "Triggered by Phase 1 validation",
      status: "planned",
      description:
        "Deployment of the on-chain parametric mutual in strict full 1:1 collateralization mode, on Arbitrum Sepolia.",
      deliverables: [
        "Parametric smart contracts in Foundry, modular IWeatherSource interface.",
        "USDC mutualization pool, Nexus Mutual style.",
        "V1 oracle aggregator (Reclaim + Chainlink).",
        "First AUG-POC → ARA conversion voted by holders.",
        "5 to 10 parametric contracts issued on testnet.",
        "On-chain voting space v1 + IPFS site + ENS URL.",
      ],
    },
    {
      id: "phase-3",
      number: "III",
      title: "Mainnet, small volumes",
      status: "planned",
      description:
        "Audits, ARA token mainnet launch, first real contracts, first iteration of the risk-weighted transition per category.",
      deliverables: [
        "Multi-pass Solidity audits (ConsenSys Diligence / Trail of Bits / OpenZeppelin / Sherlock).",
        "ARA token officially launched on mainnet.",
        "First post-genesis distribution to modelers and stakers.",
        "First batch of real contracts (drought / heatwave metropolitan France, hurricane US).",
        "Full collat → risk-weighted transition materialization for eligible categories (N ≥ 30 resolved per category).",
      ],
    },
    {
      id: "phase-4",
      number: "IV",
      title: "DePIN data layer",
      status: "planned",
      description:
        "Aratea deploys its own network of weather attestors and complements then replaces third-party bricks on relevant zones and measurement types.",
      deliverables: [
        "WeatherXM partnership or proprietary attestor network.",
        "Predictive model consumes DePIN data alongside institutional sources.",
        "Native Aratea oracle for targeted zones and types.",
        "Station operators rewarded in ARA.",
      ],
    },
    {
      id: "phase-5",
      number: "V+",
      title: "Extension",
      status: "planned",
      description:
        "Extended coverages, geographic expansion, opening of the Aratea oracle router as a brick consumable by other climate protocols.",
      deliverables: [
        "Monthly / quarterly / annual coverages, multi-geo, composite (heatwave + drought, wind + rain).",
        "Progressive geographic expansion — West Africa, Latin America, Southeast Asia.",
        "Aratea oracle aggregator becomes a brick consumable by other climate protocols.",
        "Potential partnerships with licensed insurers as fronting carriers.",
      ],
    },
  ],
  backlogTitle: "Identified backlog",
  backlog: [
    {
      priority: "P1",
      title: "Bylaws v0 project draft",
      description:
        'Target form: for-profit association under Alsace-Moselle local law. Unified voting principle (votes = floor(holder_balance)), 25% per-wallet cap, no "one person = one vote" mechanism anywhere. Evolving document until effective incorporation is triggered.',
    },
    {
      priority: "P1",
      title: "Reclaim Protocol POC",
      description:
        "Settlement test on an NWS station via attestor-core + reclaim-solidity-sdk. Absolute priority before freezing the Phase 2 oracle stack.",
    },
    {
      priority: "P1",
      title: "Trigger-driven legal memo",
      description:
        "Switzerland vs Cayman vs Alsace-Moselle comparison, triggered only when an incorporation trigger materializes.",
    },
    {
      priority: "P2",
      title: "Parametric smart contracts",
      description:
        "In Foundry. Modular IWeatherSource interface. PoolManager with strict 1:1 MCR enforced on-chain. ContractFactory, OracleResolver, GovernanceModule.",
    },
    {
      priority: "P2",
      title: "Administration and on-chain voting space",
      description:
        "Wallet connect, token holding = membership prerequisite, vote claim with KYC light, whole-token weighted voting, administrative consultation, self-modification of own data, strict confidentiality.",
    },
    {
      priority: "P2",
      title: "Site on decentralized URL",
      description:
        "IPFS hosting for public data, URL via ENS (.eth) or IPNS. Per-member modifications via wallet signature + personal write.",
    },
    {
      priority: "P2",
      title: "Differentiation sections in the white paper",
      description: '"Why Aratea and not X" — FR + EN — for Etherisc and Arbol.',
    },
    {
      priority: "P3",
      title: "Multi-pass Solidity audits",
      description:
        "ConsenSys Diligence, Trail of Bits, OpenZeppelin or Sherlock — minimum two passes.",
    },
    {
      priority: "P3",
      title: "First batch of real contracts",
      description:
        "Monthly drought / heatwave contracts by region in metropolitan France, plus a few US contracts.",
    },
  ],
  notesTitle: "Methodological notes",
  notes: [
    {
      title: "No promised dates",
      body: "Phases chained by technical milestones, not calendar dates. A phase opens only on completion of the previous one.",
    },
    {
      title: "No pre-edge fundraising",
      body: "Any external subscription stays closed until the predictive edge is validated over N > 50 fresh events.",
    },
    {
      title: "No premature incorporation",
      body: "The legal entity is created only on triggering of an explicit event. Preferred candidate: for-profit association under Alsace-Moselle local law.",
    },
    {
      title: "Radical transparency",
      body: "Anything that warrants valuation passes through a merged PR. No invisible work. Edge metrics published at each monthly round.",
    },
  ],
  status: {
    done: "DONE",
    "in-progress": "IN PROGRESS",
    planned: "PLANNED",
  },
  priority: {
    P1: "P1",
    P2: "P2",
    P3: "P3",
  },
  footer:
    "Roadmap maintained on Notion. Operational source of truth: github.com/Elladriel80/Aratea.",
  switchLabel: "FR",
};

export const fr: Content = {
  version: "v0.1",
  date: "16 mai 2026",
  hero: {
    title: "Roadmap",
    subtitle: "La trajectoire d'Aratea, ouverte et versionnée.",
    preamble:
      "Source de vérité publique sur l'état du projet et sa trajectoire. Mise à jour cadencée sur les jalons techniques, pas sur le calendrier. Complète le white paper (FR/EN v0.5) qui décrit l'architecture et le modèle.",
    quote: "« Le ciel se lit par signes. Chacun a son temps. »",
    quoteAttribution:
      "Aratos de Soles, Phaenomena, IIIᵉ siècle av. J.-C. — paraphrase.",
  },
  state: {
    title: "État au 16 mai 2026",
    doneLabel: "Fait",
    inProgressLabel: "En cours",
    done: [
      "Rebrand Augure → Aratea (11 mai 2026). Étymologie Aratos de Soles documentée.",
      "White paper FR + EN v0.5 publié sur Notion, 13 sections, gouvernance unifiée token-weighted.",
      "Repository public github.com/Elladriel80/Aratea ouvert et actif.",
      "Token AUG-POC déployé sur Arbitrum Sepolia (testnet).",
      "Capital initial Phase 1 : 1 000 USD d'ETH, financé par le porteur. Subscription externe fermée.",
      "Predictor learned_v2 livré 12 mai 2026, infrastructure gate promotable active.",
      "Discord + announce system auto sur tags Git, livré 9 mai 2026.",
      "Audit white-hat sécurité, PR #18 mergée, history rewrite, rotations Pinata + webhooks + Etherscan.",
      "Benchmark concurrents : 7 acteurs analysés (Augur, Etherisc, Arbol, Nexus Mutual, UMA, Reclaim, Polymarket).",
      "Projet de statuts v0 (FR + EN) association à but lucratif Alsace-Moselle, 40 articles.",
    ],
    inProgress: [
      "Phase 1 paper trading Kalshi — le critique reste de battre kalshi_mid sur le Brier score. Bench du 11 mai 2026 sur N=138 : learned_v2 0.1305 vs kalshi_mid 0.0845.",
      "Itération learned_v2 — feature engineering nommé, ajout/retrait de features avec mesure de delta Brier leave-one-out.",
      "Migration code-side Augure → Aratea (paths, identifiants Discord, slug repo).",
    ],
  },
  phasesTitle: "Phases",
  phases: [
    {
      id: "phase-1",
      number: "I",
      title: "Validation edge",
      subtitle: "Phase en cours — paper trading Kalshi",
      status: "in-progress",
      description:
        "Le predictor appris doit battre kalshi_mid sur le Brier score sur un test set indépendant de N > 50 événements frais. Critère honnête, écrit avant le résultat. Sans cela, le projet pivote en scope ou s'arrête proprement.",
      deliverables: [
        "Itération feature engineering jusqu'au franchissement du seuil ou épuisement des idées.",
        "POC technique Reclaim Protocol — quelques heures sur une station NWS.",
        "Switch paper → live une fois l'edge matérialisé sur N > 50.",
        "Section « Pourquoi Aratea et pas Etherisc » dans le white paper.",
      ],
    },
    {
      id: "phase-2",
      number: "II",
      title: "DAO MVP testnet",
      subtitle: "Déclenchée par la validation Phase 1",
      status: "planned",
      description:
        "Déploiement de la mutuelle paramétrique on-chain en mode full collateralization 1:1 strict, sur Arbitrum Sepolia.",
      deliverables: [
        "Smart contracts paramétriques en Foundry, interface IWeatherSource modulaire.",
        "Pool de mutualisation USDC à la Nexus Mutual.",
        "Oracle aggregator V1 (Reclaim + Chainlink).",
        "Première conversion AUG-POC → ARA votée par les holders.",
        "5 à 10 contrats paramétriques émis sur testnet.",
        "Espace de vote on-chain v1 + site IPFS + URL ENS.",
      ],
    },
    {
      id: "phase-3",
      number: "III",
      title: "Mainnet petits volumes",
      status: "planned",
      description:
        "Audits, lancement du token ARA mainnet, premiers contrats réels, première itération de la transition risk-weighted par catégorie.",
      deliverables: [
        "Audits Solidity multi-passes (ConsenSys Diligence / Trail of Bits / OpenZeppelin / Sherlock).",
        "Token ARA officiellement lancé mainnet.",
        "Première distribution post-genesis aux modelers et stakers.",
        "Premier batch de contrats réels (sécheresse / canicule France métropole, ouragan US).",
        "Matérialisation transition full collat → risk-weighted sur catégories éligibles (N ≥ 30 résolus par catégorie).",
      ],
    },
    {
      id: "phase-4",
      number: "IV",
      title: "DePIN data layer",
      status: "planned",
      description:
        "Aratea déploie son propre réseau d'attestors météo et complète puis remplace les briques tiers sur les zones et types de mesure pertinents.",
      deliverables: [
        "Partenariat WeatherXM ou réseau d'attestors propre.",
        "Modèle prédictif consomme la donnée DePIN aux côtés des sources institutionnelles.",
        "Oracle Aratea natif pour zones et types ciblés.",
        "Opérateurs de stations rétribués en ARA.",
      ],
    },
    {
      id: "phase-5",
      number: "V+",
      title: "Extension",
      status: "planned",
      description:
        "Couvertures étendues, expansion géographique, ouverture du routeur oracle Aratea comme brique consommable par d'autres protocoles climat.",
      deliverables: [
        "Couvertures mensuelles / trimestrielles / annuelles, multi-géo, composites (canicule + sécheresse, vent + pluie).",
        "Expansion géographique progressive — Afrique de l'Ouest, Amérique latine, Asie du Sud-Est.",
        "Aratea oracle aggregator devient brique consommable par d'autres protocoles climat.",
        "Partenariats potentiels avec assureurs licenciés en fronting.",
      ],
    },
  ],
  backlogTitle: "Backlog identifié",
  backlog: [
    {
      priority: "P1",
      title: "Statuts asso v0-projet",
      description:
        "Forme cible : association à but lucratif de droit local Alsace-Moselle. Principe de vote unifié (votes = floor(holder_balance)), cap 25 % par wallet, plus aucun mécanisme « 1 personne = 1 voix ». Document évolutif jusqu'à incorporation effective déclenchée par trigger.",
    },
    {
      priority: "P1",
      title: "POC Reclaim Protocol",
      description:
        "Settlement test sur une station NWS via attestor-core + reclaim-solidity-sdk. Priorité absolue avant de figer la stack oracle Phase 2.",
    },
    {
      priority: "P1",
      title: "Mémo juridique trigger-driven",
      description:
        "Comparatif Suisse vs Cayman vs Alsace-Moselle, déclenché seulement quand un trigger d'incorporation se matérialise.",
    },
    {
      priority: "P2",
      title: "Smart contracts paramétriques",
      description:
        "En Foundry. Interface IWeatherSource modulaire. PoolManager avec MCR strict 1:1 enforcé on-chain. ContractFactory, OracleResolver, GovernanceModule.",
    },
    {
      priority: "P2",
      title: "Espace d'administration et de vote on-chain",
      description:
        "Wallet connect, holding tokens = prérequis membership, claim de votes avec KYC light, vote pondéré par tokens entiers, consultation administrative, modification propres données, confidentialité stricte.",
    },
    {
      priority: "P2",
      title: "Site sur URL décentralisée",
      description:
        "Hosting IPFS pour les données publiques, URL via ENS (.eth) ou IPNS. Modifications individuelles par signature wallet + write personnel.",
    },
    {
      priority: "P2",
      title: "Sections différenciation dans le white paper",
      description: "« Pourquoi Aratea et pas X » — FR + EN — pour Etherisc et Arbol.",
    },
    {
      priority: "P3",
      title: "Audits Solidity multi-passes",
      description:
        "ConsenSys Diligence, Trail of Bits, OpenZeppelin ou Sherlock — deux passes minimum.",
    },
    {
      priority: "P3",
      title: "Premier batch de contrats réels",
      description:
        "Sécheresse / canicule mensuels département par département en France métropole, plus quelques contrats US.",
    },
  ],
  notesTitle: "Notes méthodologiques",
  notes: [
    {
      title: "Pas de date promise",
      body: "Les phases sont enchaînées par jalons techniques, pas par calendrier. Une phase ne s'ouvre que sur complétion de la précédente.",
    },
    {
      title: "Pas de levée pré-edge",
      body: "Toute subscription externe reste fermée tant que l'edge prédictif n'est pas validé sur N > 50 événements frais.",
    },
    {
      title: "Pas d'incorporation prématurée",
      body: "L'entité légale ne sera créée qu'au déclenchement d'un trigger explicite. Candidat préféré : association à but lucratif de droit local Alsace-Moselle.",
    },
    {
      title: "Transparence radicale",
      body: "Tout ce qui mérite valuation passe par un PR mergé. Pas de travail invisible. Métriques de l'edge publiées à chaque round mensuel.",
    },
  ],
  status: {
    done: "FAIT",
    "in-progress": "EN COURS",
    planned: "PLANIFIÉ",
  },
  priority: {
    P1: "P1",
    P2: "P2",
    P3: "P3",
  },
  footer:
    "Roadmap maintenue sur Notion. Source de vérité opérationnelle : github.com/Elladriel80/Aratea.",
  switchLabel: "EN",
};

export const dict: Record<Locale, Content> = { fr, en };
