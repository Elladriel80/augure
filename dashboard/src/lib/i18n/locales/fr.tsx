import type { ReactNode } from "react";

import type { Dictionary } from "./en";

// French dictionary. Must satisfy the Dictionary type derived from en.tsx.
export const fr: Dictionary = {
  layout: {
    nav: {
      predictor: "prédicteur",
      token: "token",
      rounds: "rounds",
      github: "github ↗",
    },
    footer:
      "Vue lecture seule. Pas de wallet, pas de transactions. Données rafraîchies à chaque chargement.",
  },

  common: {
    not_deployed_title: "Contrats pas encore déployés",
    not_deployed_body: (
      <>
        Définis <code>NEXT_PUBLIC_TOKEN_ADDRESS</code> et{" "}
        <code>NEXT_PUBLIC_REGISTRY_ADDRESS</code> dans l&apos;environnement une
        fois que le script de déploiement M4 aura tourné sur Arbitrum Sepolia.
        Le dashboard lira alors l&apos;état live au prochain refresh.
      </>
    ),
    not_deployed_short: "Contrats pas encore déployés.",
  },

  token: {
    metrics: {
      total_supply: "Supply totale",
      total_supply_hint: (wei: string) => `${wei} wei`,
      pause_state: "État pause",
      paused: "EN PAUSE",
      active: "actif",
      paused_hint:
        "Les transferts user-to-user sont bloqués. Mint et burn restent opérationnels.",
      active_hint: "Les transferts user-to-user sont autorisés.",
      contract: "Contrat token",
      contract_hint:
        "Vérifié sur l’explorateur si `forge verify-contract` a été lancé.",
    },
    cap: {
      heading: (month: string) => `Cap mensuel — ${month}`,
      supply_at_month_start: "Supply au début du mois",
      supply_at_month_start_hint_bound:
        "Snapshot pris au premier executeRound du mois.",
      supply_at_month_start_hint_genesis:
        "Exception genesis — pas encore de snapshot.",
      minted_this_month: "Minté ce mois",
      minted_hint_bound: (pct: string) => `${pct} du cap 10%`,
      minted_hint_unbound: "Cap non contraignant ce mois.",
      remaining_margin: "Marge restante",
      remaining_unconstrained: "non contraint",
      remaining_hint_bound: (cap: string) => `Cap = ${cap}`,
      remaining_hint_unbound: "Exception genesis",
    },
    rounds: {
      heading: "Rounds",
      intro: (link: ReactNode) => (
        <>
          Cycle de vie de chaque round de mint mensuel. Voir {link} pour la
          liste complète.
        </>
      ),
      intro_link: "la page rounds",
      registry_label: "Registre :",
    },
  },

  rounds: {
    title: "Rounds",
    intro:
      "Chaque round committé au registre, trié par date de proposition (plus récent en premier).",
    empty: (
      <>
        Aucun round proposé pour le moment. Le premier apparaîtra ici dès que le
        founder aura lancé{" "}
        <code className="text-text">script/ProposeGenesisRound.s.sol</code>.
      </>
    ),
    table: {
      round: "Round",
      status: "Statut",
      proposed: "Proposé",
      window_ends: "Fin de fenêtre",
      total_amount: "Montant total",
      beneficiaries: "Bénéficiaires",
    },
  },

  round_detail: {
    back: "← tous les rounds",
    title: "Détail du round",
    fields: {
      status: "Statut",
      status_numeric: "Statut (numérique)",
      proposed_at: "Proposé le (UTC)",
      challenge_window: "Fenêtre de challenge",
      challenge_window_value: (days: number) => `${days} jours`,
      challenge_window_hint: (date: string) => `fin ${date}`,
      beneficiaries: "Bénéficiaires",
      total_to_mint: "Total à minter",
    },
    window_label: "Fenêtre",
    allocation: "Allocation",
    allocation_table: {
      index: "#",
      beneficiary: "Bénéficiaire",
      amount: "Montant",
    },
    offchain: "Artefacts off-chain",
    ipfs_uri: "URI IPFS :",
    ipfs_none: "(aucune)",
    ipfs_help: (
      <>
        L&apos;URI IPFS pointe sur le <code>valuation_report.md</code> pinné. Le
        roundHash est{" "}
        <code>keccak256(abi.encode(beneficiaries, amounts, ipfsUri))</code> —
        n&apos;importe qui peut le re-dériver depuis ces inputs et vérifier le
        commitment on-chain.
      </>
    ),
  },

  predictor: {
    title: "Prédicteur — boucle d’apprentissage",
    intro: (
      <>
        Aratea est un moteur de découverte de facteurs météo. Chaque feature
        nommée ici est une hypothèse ; chaque run d&apos;entraînement mesure si
        elle porte du signal. Le benchmark est le Brier de{" "}
        <code className="text-text">kalshi_mid</code> sur le même row-set —
        battre le marché, sur son propre terrain.
      </>
    ),
    counters: {
      features_tracked: "Features suivies",
      active: "Actives",
      experimental: "Expérimentales",
      dropped: "Abandonnées",
      paper_bets: "Paper bets (ouverts / résolus)",
      phase_1_hint: (n: number | string) => `Phase 1 : ${n}`,
    },
    manifest_generated: (ts: string, v: number) =>
      `Manifest généré le ${ts} (schéma v${v}).`,
    manifest_missing_title: "Manifest prédicteur introuvable",
    manifest_missing_body: (
      <>
        L&apos;étape de build qui génère{" "}
        <code className="text-text">public/predictor_manifest.json</code> n&apos;a
        pas tourné. Lance <code className="text-text">npm run manifest</code>{" "}
        (ou un <code className="text-text">npm run build</code> complet) puis
        recharge.
      </>
    ),
    sections: {
      live_title: "A. Runs live (paper trades Kalshi)",
      live_desc:
        "Chaque ligne est un vrai paper trade sur Kalshi. Le champion prend la position (vraie ligne de ledger, vrai P&L) ; les challengers et baselines tournent en shadow mode pour comparaison Brier. ★ marque le meilleur Brier sur un run donné. La règle de promotion (swap du champion) demande une dominance Brier en moyenne glissante sur N≥10 trades résolus — un seul run gagné reste anecdotique.",
      factors_title: "B. Facteurs nommés",
      factors_desc:
        "Chaque ligne est une hypothèse nommée utilisée par le prédicteur appris à l’entraînement. Brier Δ est le delta leave-one-out du run d’entraînement le plus récent — trier dessus pour voir ce qui a porté le modèle.",
      latest_title: "C. Dernier run d’entraînement",
      latest_desc: (
        <>
          Snapshot du dernier fit sklearn du prédicteur appris sur les
          résolutions historiques. Ce n&apos;est <em>pas</em> un paper trade —
          c&apos;est une passe de cross-validation pour voir si le feature set
          actuel a un edge sur kalshi_mid sur les events Kalshi passés.
        </>
      ),
      latest_empty: "Aucun run d’entraînement pour le moment.",
      history_title: "D. Historique des runs d’entraînement",
      history_desc: (
        <>
          Chaque passe d&apos;entraînement sklearn, plus récente en premier.{" "}
          <em>Ce n&apos;est pas l&apos;historique des paper trades</em> — voir
          section A pour ça. Un run d&apos;entraînement avec Brier test sous
          Brier kalshi_mid sur les mêmes rows signifie que le modèle a du signal
          au-delà du mid de marché en cross-validation.
        </>
      ),
      brier_title: "E. Trajectoire du Brier d’entraînement",
      brier_desc:
        "Modèle appris (test) vs kalshi_mid (mêmes rows de test) sur tous les runs d’entraînement. La ligne horizontale en pointillé est le Brier kalshi_mid le plus récent comme référence absolue ; les marqueurs verticaux en pointillé signalent un bump de feature set (v0 → v1 → v2 …).",
    },
  },

  status: {
    none: "Inconnu",
    proposed: "Proposé",
    challenged: "Challengé",
    executed: "Exécuté",
    cancelled: "Annulé",
  },

  components: {
    live_table: {
      empty: (
        <>
          Aucun paper trade live pour le moment. Le premier sera le prochain run
          de <code className="text-text">daily_auto.py</code>.
        </>
      ),
      header_run: "Run",
      header_when: "Quand",
      header_event: "Event / Bin",
      header_side: "Side",
      header_champion: "Champion p",
      header_challenger: "Challenger p",
      header_baseline: "Baseline p",
      header_kalshi_mid: "kalshi_mid",
      header_outcome: "Résultat",
      header_pnl: "P&L paper",
      pending: "EN ATTENTE",
      win: (outcome: string) => `GAGNÉ (${outcome.toUpperCase()})`,
      loss: (outcome: string) => `PERDU (${outcome.toUpperCase()})`,
      footer:
        "★ = meilleur Brier sur ce run · B = score Brier par modèle · P&L = champion seul (challengers et baselines en shadow, pas d'exposition réelle).",
    },
    history_table: {
      empty: "Aucun run d’entraînement pour le moment.",
      header_when: "Quand (UTC)",
      header_feature_set: "Feature set",
      header_n_test: "n_test",
      header_brier_test: "Brier test",
      header_brier_kalshi_mid: "Brier kalshi_mid",
      header_gap: "Gap",
      header_verdict: "Verdict",
      header_notes: "Notes",
    },
    feature_table: {
      header_name: "Nom",
      header_hypothesis: "Hypothèse",
      header_source: "Source",
      header_added: "Ajouté",
      header_delta: "Brier Δ",
      header_status: "Statut",
      modal_feature: "Feature",
      modal_hypothesis: "Hypothèse",
      modal_status: "Statut",
      modal_date_added: "Date d’ajout",
      modal_source: "Source",
      modal_current_delta: "Brier Δ actuel",
      modal_history: "Historique",
      modal_history_empty: "Pas encore mesurée dans aucun run d’entraînement.",
      modal_history_run: "Run",
      modal_history_feature_set: "Feature set",
      modal_close: "fermer",
      modal_close_aria: "Fermer",
    },
    feature_table_footer: (carried: ReactNode, noise: ReactNode) => (
      <>
        Clique sur une ligne pour l&apos;hypothèse complète, le lien source et
        l&apos;historique par run. Brier Δ est le delta leave-one-out du Brier
        test du dernier run —
        {carried} = la feature a porté du signal,
        {noise} = bruit net sur cette split.
      </>
    ),
    feature_table_footer_carried: " négatif (↓) ",
    feature_table_footer_noise: " positif (↑) ",
    latest_card: {
      title: "Dernier run d’entraînement",
      feature_set: "feature set",
      notes: "notes",
    },
    verdict: {
      ensemble: "L’ENSEMBLE GAGNE",
      market: "LE MARCHÉ GAGNE",
      tie: "ÉGALITÉ",
      tooltip:
        "Comparaison du Brier sur le test set vs kalshi_mid sur les mêmes rows",
    },
    countdown: {
      expired: "fenêtre expirée",
      remaining: "restant",
    },
    brier_chart: {
      empty: (
        <>
          Aucun run d&apos;entraînement pour le moment. La première exécution de{" "}
          <code className="text-text">train_learned.py</code> remplira ce
          graphe.
        </>
      ),
      axis_x: "run (date UTC)",
      axis_y: "score Brier (plus bas = mieux)",
      legend_learned: "appris (test)",
      legend_kalshi: "kalshi_mid (test)",
    },
  },

  locale_toggle: {
    en: "EN",
    fr: "FR",
    aria: "Changer de langue",
  },
};
