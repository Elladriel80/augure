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
    emission: {
      heading: "Politique d'émission",
      body:
        "Aucun cap d'émission n'est appliqué on-chain. Le token Aratea représente une part patrimoniale et un droit de gouvernance ; il n'a pas vocation à être tradé sur marché secondaire, donc un cap référencé au supply pour protéger un prix de marché est sans objet. La qualité de l'émission est garantie off-chain par le rubric de valuation, le vote pondéré des holders sur toute valuation individuelle > 0,01 BTC, le cooldown nouveaux entrants, le slashing et l'audit annuel.",
      reference:
        "Références : white paper §7.7, statuts art. 31 et art. 32, et la promesse de couverture bornée (statuts art. 4 bis) — le ratio engagements/capital est lisible on-chain en temps réel.",
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
    layers: {
      aria: "Choisir le niveau de détail",
      level_1: { label: "Niveau 1 · Public", hint: "Ce qu’Aratea pense, en clair" },
      level_2: { label: "Niveau 2 · Averti", hint: "Composantes nommées, stats simples" },
      level_3: { label: "Niveau 3 · Expert", hint: "Registry complet, Brier, runs bruts" },
      cta_why: "Pourquoi Aratea pense ça ? →",
      cta_more: "Voir le registry complet →",
    },
    public: {
      heading: "Ce qu’Aratea pense aujourd’hui",
      no_run: "Pas encore de prévision live — repasse après le prochain run quotidien.",
      question_label: "La question du jour",
      probability_caption: "Probabilité selon Aratea que la réponse soit OUI",
      market_says: "Le marché paie OUI à",
      aratea_says: "Aratea estime OUI à",
      side_yes: "Aratea parie OUI",
      side_no: "Aratea parie NON",
      agrees: "Aratea est d’accord avec le marché",
      disagrees_higher: (gap: string) =>
        `Aratea pense que OUI est ${gap} plus probable que ce que dit le marché`,
      disagrees_lower: (gap: string) =>
        `Aratea pense que OUI est ${gap} moins probable que ce que dit le marché`,
      confidence_label: "Confiance",
      confidence_low: "Faible",
      confidence_medium: "Moyenne",
      confidence_high: "Forte",
      confidence_low_hint: "Le modèle est proche du pile ou face sur celui-ci.",
      confidence_medium_hint: "Le modèle a une opinion claire mais pas extrême.",
      confidence_high_hint: "Le modèle est très sûr du résultat.",
      explainer_title: "Comment lire cette carte",
      explainer_body: (
        <>
          Le grand nombre est la probabilité qu’Aratea attribue à la réponse{" "}
          <em>oui</em>. Le nombre du marché, c’est ce que les gens sur Kalshi
          paient pour le même pari en ce moment. Quand les deux divergent,
          Aratea prend le côté qu’elle croit mal coté. Phase 1 = paper money
          uniquement, aucun vrai pari n’est placé.
        </>
      ),
      window_open: "Pari ouvert — résultat pas encore connu",
      window_resolved_won: "Pari clos — Aratea a gagné",
      window_resolved_lost: "Pari clos — Aratea a perdu",
      champion_caption: (name: string) =>
        `Pari placé par le modèle « ${name} » (champion actuel).`,
      champion_explainer_title: "Pourquoi ce modèle et pas un autre ?",
      champion_explainer:
        "Aratea fait tourner plusieurs modèles en parallèle. Seul le champion place les paris (paper) ; les challengers tournent en shadow tant qu’ils n’ont pas battu le champion sur la durée. D’autres modèles peuvent estimer une probabilité différente — voir le niveau 2 pour comparer.",
      question_template: (variable: string, location: string, date: string, threshold: string) =>
        `La ${variable} à ${location} le ${date} tombera-t-elle dans le bin ${threshold} ?`,
      threshold_unit_temp_f: (n: string) => `${n}°F`,
      threshold_unit_in: (n: string) => `${n} in`,
      threshold_unit_mph: (n: string) => `${n} mph`,
      threshold_unit_count: (n: string) => `${n} occurrences`,
      threshold_unit_raw: (n: string) => n,
      var_lowt: "température minimale",
      var_hight: "température maximale",
      var_temp: "température",
      var_rain: "pluie",
      var_snow: "chute de neige",
      var_wind: "vitesse du vent",
      var_hurr: "nombre d’ouragans",
    },
    informed: {
      heading: "Ce qui entre dans le chiffre d’Aratea",
      intro: (
        <>
          Aratea fait tourner <em>plusieurs</em> modèles de prévision en
          parallèle. Chaque carte ci-dessous est une estimation indépendante de
          la même question : « quelle est la probabilité que ça arrive ? ». Les
          chiffres <strong>ne s’additionnent pas</strong> à 100 % — ce sont
          plusieurs façons différentes de deviner la même réponse. Un seul —
          le <strong>champion</strong> — place réellement le pari ; les autres
          tournent en shadow.
        </>
      ),
      components_subheading: "Les estimations parallèles d’Aratea",
      market_subheading: "Ce que paie le marché",
      market_subheading_hint:
        "Affiché pour comparaison. C’est le benchmark qu’Aratea cherche à battre — ce n’est pas l’une de ses entrées.",
      component_climatology: "Taux historique",
      component_climatology_desc:
        "À quelle fréquence l’événement s’est produit le même jour de l’année sur les 15 dernières années. Le prior bête mais honnête que toute prévision doit battre.",
      component_forecast_blend: "Modèle météo court terme",
      component_forecast_blend_desc:
        "La prévision déterministe Open-Meteo autour de la date cible, mélangée au taux historique selon l’horizon.",
      component_ensemble: "Ensemble multi-modèles",
      component_ensemble_desc:
        "Moyenne de quatre modèles vendeurs (ECMWF, GraphCast, GFS, JMA). Utile comme baseline lissée.",
      component_learned: "Modèle appris",
      component_learned_desc:
        "Une petite régression qui apprend combien de poids donner à chaque composante à partir des résolutions passées. C’est avec celui-là qu’Aratea parie.",
      market_label: "Marché (Kalshi mid)",
      market_desc:
        "Ce que le carnet d’ordres Kalshi implique en ce moment. L’étalon qu’Aratea doit battre.",
      no_run: "Pas encore de run d’entraînement — les composantes apparaîtront dès le premier fit.",
      role_champion: "champion",
      role_challenger: "challenger",
      role_baseline: "baseline",
      role_explainer:
        "Champion = le modèle dont la probabilité sert effectivement à placer le pari. Les challengers tournent en parallèle, en shadow ; l’un d’eux ne devient champion qu’après avoir battu le précédent sur une fenêtre glissante de trades résolus. C’est pour ça que la probabilité du « champion » affichée en vue publique peut différer de celle du « modèle appris » ici.",
      brier_chart_heading: "Bilan jusqu’ici",
      brier_intro: (
        <>
          Le graphe ci-dessous montre le <strong>score Brier</strong> de deux
          prévisionnistes sur tous les passages d’entraînement. Le Brier mesure
          la précision : 0 = parfait, 1 = toujours faux, plus bas = meilleur.
          <br />
          <span className="text-[#5fa8d3]">●</span> ligne bleue = le modèle
          appris d’Aratea.{" "}
          <span className="text-[#e2b341]">●</span> ligne jaune = le mid de
          marché Kalshi sur exactement les mêmes événements. Quand la bleue
          reste sous la jaune, Aratea a du signal que le carnet d’ordres n’a
          pas.
        </>
      ),
    },
    expert: {
      heading: "Vue expert",
      intro:
        "Tout ce que porte le manifest : facteurs nommés avec leur delta leave-one-out, ledger des paper trades, runs d’entraînement et trajectoire Brier. C’est la vue météorologiste / actuaire — pas d’arrondi, pas de pédagogie.",
    },
    n_eff_section: {
      title: "Échantillon hybride N_eff",
      n_live: "N_live (paper trades réels)",
      n_backtest_strict: "N_backtest_strict (replay point-in-time)",
      n_backtest_naive_excluded: "Exclus NAIVE (informatif)",
      decomposition: (
        nLive: number,
        alpha: number,
        nBacktest: number,
        nEff: number,
      ) =>
        `= ${nLive} + ${alpha} × ${nBacktest} = ${nEff.toFixed(1)}`,
      compact_hint: (nLive: number, alpha: number, nBacktest: number) =>
        `= ${nLive} live + ${alpha} × ${nBacktest} backtest. Décisions secondaires seulement — le gate Phase 1 reste sur le live.`,
      phase_1_gate: (nLive: number, gate: number) =>
        `Gate Phase 1 (strict, live seul) : N_live ≥ ${gate}. Actuellement ${nLive}/${gate}.`,
      phase_1_reached: "Gate Phase 1 atteint (live seul) ✓",
      methodology_note:
        "N_eff sert aux décisions secondaires — sélection de feature set, courbes de calibration, check de promotion complémentaire. Le gate Phase 1 go/no-go reste strictement sur N_live ; le volume backtest ne s’y substitue jamais.",
      convention_link: "Lire CONVENTION §6.bis",
    },
    filters: {
      series_label: "Série",
      status_label: "Statut",
      clear: "Effacer",
      status_open: "ouvert",
      status_resolved: "résolu",
    },
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
      backtest_title: "F. Runs backtest (replay)",
      backtest_desc:
        "Records replayés par backtest.py sur des events Kalshi déjà résolus. Seuls les records strict point-in-time comptent dans N_backtest_strict ; les runs NAIVE sont flagués et exclus de l’échantillon hybride. Les filtres ci-dessus s’appliquent à la fois ici et à la section live.",
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
    backtest_table: {
      empty:
        "Aucun replay backtest dans le manifest. Le compteur agrégé peut rester non-nul — le builder du manifest tronque le détail par-record quand le ledger dépasse le budget inline.",
      header_run: "Run",
      header_when: "As-of → cible",
      header_event: "Série / Bin",
      header_mode: "Mode",
      header_model: "Modèle p / Brier",
      header_outcome: "Résultat",
      pending: "EN ATTENTE",
      win: "GAGNÉ",
      loss: "PERDU",
      footer:
        "★ = meilleur Brier sur ce replay · B = score Brier · NAIVE = exclu de N_backtest_strict.",
      load_more: "Charger 25 de plus",
      showing_template: "Affiche {visible} sur {total}",
      naive_label: "NAIVE",
      naive_tooltip: "Exclu de N_backtest_strict (CONVENTION §6.bis)",
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
