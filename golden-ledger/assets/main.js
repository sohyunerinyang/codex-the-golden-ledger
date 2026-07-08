document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector(".nav-toggle");
  const navLinks = document.querySelector(".nav-links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  const money = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const sigmoid = (value) => 1 / (1 + Math.exp(-value));
  const logit = (value) => Math.log(value / (1 - value));
  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  const losFelizMarket = {
    label: "Los Feliz / 90027",
    parcel: "APN 5588-014-021",
    center: [34.1122, -118.2873],
    zoom: 14,
    source: "Live OpenStreetMap base layer with Golden Ledger APN, CFD, and FHSZ analytical overlays.",
    apn: [
      [34.1141, -118.2917],
      [34.1134, -118.2848],
      [34.1097, -118.2855],
      [34.1104, -118.2924]
    ],
    cfd: [
      [34.1174, -118.2941],
      [34.1163, -118.2828],
      [34.1077, -118.2844],
      [34.1083, -118.2960]
    ],
    fire: [
      [34.1195, -118.2898],
      [34.1160, -118.2785],
      [34.1052, -118.2808],
      [34.1089, -118.2927]
    ]
  };

  function initHeroMiniMap() {
    const mapNode = document.getElementById("heroMiniMap");
    if (!mapNode || !window.L) return;

    const gold = cssVar("--gold-dark") || "#765b23";
    const red = cssVar("--red") || "#8e3e35";
    const ink = cssVar("--ink") || "#181713";
    const map = L.map(mapNode, {
      attributionControl: false,
      zoomControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false,
      touchZoom: false
    }).setView(losFelizMarket.center, 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19
    }).addTo(map);

    L.polygon(losFelizMarket.cfd, {
      color: gold,
      weight: 2,
      fillColor: gold,
      fillOpacity: 0.13,
      interactive: false
    }).addTo(map);

    L.polygon(losFelizMarket.fire, {
      color: red,
      weight: 2,
      fillColor: red,
      fillOpacity: 0.12,
      interactive: false
    }).addTo(map);

    L.polygon(losFelizMarket.apn, {
      color: ink,
      weight: 1.5,
      fillColor: "#fbfaf7",
      fillOpacity: 0.34,
      interactive: false
    }).addTo(map);

    L.circleMarker(losFelizMarket.center, {
      radius: 7,
      color: "#fbfaf7",
      fillColor: red,
      fillOpacity: 1,
      weight: 2,
      interactive: false
    }).addTo(map);

    setTimeout(() => map.invalidateSize(), 120);
  }

  function initLedgerMap() {
    const mapNode = document.getElementById("ledgerMap");
    if (!mapNode || !window.L) return;

    const markets = {
      "los-feliz": losFelizMarket,
      "palo-alto": {
        label: "Palo Alto / 94301",
        parcel: "APN 120-11-046",
        center: [37.4443, -122.1598],
        zoom: 14,
        source: "Live OpenStreetMap base layer with Peninsula parcel and wildfire interface overlays.",
        apn: [
          [37.4460, -122.1632],
          [37.4466, -122.1564],
          [37.4417, -122.1558],
          [37.4412, -122.1626]
        ],
        cfd: [
          [37.4495, -122.1655],
          [37.4490, -122.1540],
          [37.4380, -122.1542],
          [37.4388, -122.1664]
        ],
        fire: [
          [37.4523, -122.1716],
          [37.4498, -122.1580],
          [37.4395, -122.1604],
          [37.4420, -122.1746]
        ]
      },
      "irvine": {
        label: "Irvine / 92618",
        parcel: "APN 591-421-18",
        center: [33.6652, -117.7440],
        zoom: 14,
        source: "Live OpenStreetMap base layer with Irvine CFD and fire-hazard planning overlays.",
        apn: [
          [33.6675, -117.7489],
          [33.6682, -117.7408],
          [33.6626, -117.7399],
          [33.6621, -117.7481]
        ],
        cfd: [
          [33.6714, -117.7524],
          [33.6717, -117.7365],
          [33.6589, -117.7358],
          [33.6578, -117.7511]
        ],
        fire: [
          [33.6725, -117.7468],
          [33.6674, -117.7318],
          [33.6552, -117.7372],
          [33.6602, -117.7543]
        ]
      }
    };

    const gold = cssVar("--gold-dark") || "#765b23";
    const red = cssVar("--red") || "#8e3e35";
    const ink = cssVar("--ink") || "#181713";
    const map = L.map(mapNode, {
      zoomControl: false,
      scrollWheelZoom: false
    }).setView(markets["los-feliz"].center, markets["los-feliz"].zoom);

    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const groups = {
      apn: L.layerGroup().addTo(map),
      cfd: L.layerGroup().addTo(map),
      fire: L.layerGroup().addTo(map)
    };

    const marker = L.circleMarker(markets["los-feliz"].center, {
      radius: 9,
      color: ink,
      fillColor: ink,
      fillOpacity: 1,
      weight: 2
    }).addTo(map);

    const marketLabel = document.getElementById("mapMarketLabel");
    const parcelLabel = document.getElementById("mapParcelLabel");
    const sourceLabel = document.getElementById("mapSourceLabel");

    function drawMarket(key) {
      const market = markets[key] || markets["los-feliz"];
      Object.values(groups).forEach((group) => group.clearLayers());
      L.polygon(market.apn, {
        color: ink,
        weight: 1.4,
        fillColor: "#fbfaf7",
        fillOpacity: 0.38
      }).addTo(groups.apn).bindPopup(`<div class="ledger-popup"><span>Subject parcel</span><strong>${market.parcel}</strong>APN layer shown against live street-map context.</div>`);

      L.polygon(market.cfd, {
        color: gold,
        weight: 2,
        fillColor: gold,
        fillOpacity: 0.17
      }).addTo(groups.cfd).bindPopup(`<div class="ledger-popup"><span>Mello-Roos / CFD</span><strong>Special-tax perimeter</strong>Community Facilities District exposure modeled as a separate monthly ledger line.</div>`);

      L.polygon(market.fire, {
        color: red,
        weight: 2,
        fillColor: red,
        fillOpacity: 0.15
      }).addTo(groups.fire).bindPopup(`<div class="ledger-popup"><span>FHSZ overlay</span><strong>Wildfire risk layer</strong>Fire Hazard Severity Zone input used to pressure-test insurance assumptions.</div>`);

      marker.setLatLng(market.center);
      marker.bindPopup(`<div class="ledger-popup"><span>${market.label}</span><strong>${market.parcel}</strong>Subject property marker connected to the Golden Ledger buyer workflow.</div>`);
      map.setView(market.center, market.zoom, { animate: true });
      if (marketLabel) marketLabel.textContent = market.label;
      if (parcelLabel) parcelLabel.textContent = market.parcel;
      if (sourceLabel) sourceLabel.textContent = market.source;
    }

    document.querySelectorAll("[data-ledger-layer]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.ledgerLayer;
        button.classList.toggle("active");
        if (button.classList.contains("active")) {
          groups[key]?.addTo(map);
        } else {
          groups[key]?.removeFrom(map);
        }
      });
    });

    const marketSelect = document.getElementById("marketSelect");
    marketSelect?.addEventListener("change", () => drawMarket(marketSelect.value));
    drawMarket("los-feliz");
    setTimeout(() => map.invalidateSize(), 100);
  }

  initHeroMiniMap();
  initLedgerMap();

  const timelineItems = [...document.querySelectorAll(".timeline li")];
  if (timelineItems.length && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    let activeTimelineIndex = 0;
    const advanceTimelineHover = () => {
      timelineItems.forEach((item, index) => {
        item.classList.toggle("is-active", index === activeTimelineIndex);
      });
      activeTimelineIndex = (activeTimelineIndex + 1) % timelineItems.length;
    };
    advanceTimelineHover();
    setInterval(advanceTimelineHover, 2400);
  }

  function calculateWinProbability(listing, offer) {
    const marketPremium = 0.042;
    const daysOnMarketRelief = -0.08;
    const competitorPressure = Math.log1p(5) / Math.log(11);
    const buyerPremium = offer / listing - 1;
    return clamp(sigmoid(-0.18 + buyerPremium * 26 - marketPremium * 12 - competitorPressure * 1.15 + daysOnMarketRelief * 0.82), 0.01, 0.97);
  }

  function renderOfferTargets(listing) {
    const targets = document.getElementById("offerTargets");
    if (!targets) return;
    const marketPremium = 0.042;
    const competitorPressure = Math.log1p(5) / Math.log(11);
    const daysOnMarketRelief = -0.08;
    targets.innerHTML = [0.6, 0.85, 0.95].map((target) => {
      const premium = (logit(target) + 0.18 + marketPremium * 12 + competitorPressure * 1.15 - daysOnMarketRelief * 0.82) / 26;
      return `<div><span>${Math.round(target * 100)}% target</span><strong>${money.format(listing * (1 + premium))}</strong></div>`;
    }).join("");
  }

  const offerSlider = document.getElementById("offerSlider");
  if (offerSlider) {
    const listingInput = document.getElementById("listingPrice");
    const offerOutput = document.getElementById("offerOutput");
    const winRate = document.getElementById("winRate");
    const winFill = document.getElementById("winFill");

    const updateOffer = () => {
      const listing = Number(listingInput.value) || 880000;
      const offer = Number(offerSlider.value);
      const probability = calculateWinProbability(listing, offer);
      offerOutput.textContent = money.format(offer);
      winRate.textContent = `${(probability * 100).toFixed(1)}%`;
      winFill.style.width = `${probability * 100}%`;
      winFill.style.background = probability >= 0.8 ? "var(--green)" : probability >= 0.55 ? "var(--amber)" : "var(--red)";
      renderOfferTargets(listing);
    };

    listingInput.addEventListener("input", () => {
      const listing = Number(listingInput.value) || 880000;
      offerSlider.min = String(listing);
      offerSlider.max = String(Math.round(listing * 1.18));
      offerSlider.value = String(Math.round(listing * 1.05));
      updateOffer();
    });
    offerSlider.addEventListener("input", updateOffer);
    updateOffer();
  }

  const homeAge = document.getElementById("homeAge");
  if (homeAge) {
    const ageOutput = document.getElementById("ageOutput");
    const material = document.getElementById("material");
    const seismicRisk = document.getElementById("seismicRisk");
    const seismicOutput = document.getElementById("seismicOutput");
    const riskPill = document.getElementById("riskPill");
    const emvValue = document.getElementById("emvValue");
    const briefText = document.getElementById("briefText");

    const updateRisk = () => {
      const age = Number(homeAge.value);
      const seismic = Number(seismicRisk.value) / 100;
      const materialText = material.value.toLowerCase();
      const materialFactor = materialText.includes("masonry") ? 1.34 : materialText.includes("wood") ? 1.22 : 1.02;
      const emv = 65000 * (0.55 + clamp(age / 100, 0.05, 1.55) * 1.15 + seismic * 1.85 + (materialFactor - 1) * 1.45);
      const risk = clamp(0.22 + age / 100 * 0.28 + seismic * 0.31 + (materialFactor - 1) * 0.24, 0.05, 1);
      ageOutput.textContent = `${age} yrs`;
      seismicOutput.textContent = `${Math.round(seismic * 100)}%`;
      emvValue.textContent = money.format(emv);

      if (risk >= 0.62) {
        riskPill.textContent = "Elevated Exposure";
        riskPill.className = "status risk";
        briefText.textContent = "Do not waive casually. The property profile carries compounded seismic, age, and construction exposure; a clean offer can transfer six-figure latent liability onto the buyer.";
      } else if (risk >= 0.42) {
        riskPill.textContent = "Moderate Exposure";
        riskPill.className = "status warn";
        briefText.textContent = "Waiver is possible only with disciplined reserves. Inspection certainty has direct monetary value on this asset.";
      } else {
        riskPill.textContent = "Contained Exposure";
        riskPill.className = "status safe";
        briefText.textContent = "Waiver risk is comparatively contained, though unknown systems and coverage volatility should remain priced into the offer posture.";
      }
    };

    [homeAge, material, seismicRisk].forEach((node) => node.addEventListener("input", updateRisk));
    updateRisk();
  }

  const homePrice = document.getElementById("homePrice");
  if (homePrice) {
    const annualIncome = document.getElementById("annualIncome");
    const downPayment = document.getElementById("downPayment");
    const mortgageRate = document.getElementById("mortgageRate");
    const melloRoos = document.getElementById("melloRoos");
    const fireTier = document.getElementById("fireTier");
    const fireTierOutput = document.getElementById("fireTierOutput");
    const costLines = document.getElementById("costLines");
    const dtiValue = document.getElementById("dtiValue");
    const dtiStatus = document.getElementById("dtiStatus");
    const dtiFill = document.getElementById("dtiFill");
    const firePremium = { 1: 1800, 2: 2700, 3: 4200, 4: 6900, 5: 10200 };

    const mortgagePayment = (principal, annualRate) => {
      const rate = annualRate / 12;
      const periods = 360;
      if (rate === 0) return principal / periods;
      return principal * rate * (1 + rate) ** periods / ((1 + rate) ** periods - 1);
    };

    const updateCosts = () => {
      const price = Number(homePrice.value) || 0;
      const income = Number(annualIncome.value) || 1;
      const down = Number(downPayment.value) || 0;
      const rate = Number(mortgageRate.value) || 0.065;
      const pi = mortgagePayment(Math.max(price - down, 1), rate);
      const tax = price * 0.0125 / 12;
      const cfd = melloRoos.checked ? 250 : 0;
      const fire = firePremium[Number(fireTier.value)] / 12;
      const monthly = pi + tax + cfd + fire;
      const dti = monthly / (income / 12);
      fireTierOutput.textContent = fireTier.value;
      costLines.innerHTML = `
        <div><span>Principal & interest</span><strong>${money.format(pi)}/mo</strong></div>
        <div><span>Prop 13 + county bonds</span><strong>${money.format(tax)}/mo</strong></div>
        <div><span>Mello-Roos CFD</span><strong>${cfd ? money.format(cfd) + "/mo" : "Not applied"}</strong></div>
        <div><span>Fire-zone insurance</span><strong>${money.format(fire)}/mo</strong></div>
      `;
      dtiValue.textContent = `${(dti * 100).toFixed(1)}%`;
      dtiFill.style.width = `${clamp(dti * 100, 0, 100)}%`;

      if (dti > 0.43) {
        dtiStatus.textContent = "DTI breached";
        dtiFill.style.background = "var(--red)";
      } else if (dti >= 0.36) {
        dtiStatus.textContent = "Warning";
        dtiFill.style.background = "var(--amber)";
      } else {
        dtiStatus.textContent = "Safe";
        dtiFill.style.background = "var(--green)";
      }
    };

    [homePrice, annualIncome, downPayment, mortgageRate, melloRoos, fireTier].forEach((node) => {
      node.addEventListener("input", updateCosts);
      node.addEventListener("change", updateCosts);
    });
    updateCosts();
  }

  document.querySelectorAll(".tier-select").forEach((link) => {
    link.addEventListener("click", () => {
      const tier = document.getElementById("tierInterest");
      if (tier) tier.value = link.dataset.tier;
    });
  });

  document.querySelectorAll("select[data-no-default]").forEach((select) => {
    select.selectedIndex = -1;
  });

  const inquiryForm = document.getElementById("inquiryForm");
  if (inquiryForm) {
    inquiryForm.addEventListener("submit", (event) => {
      event.preventDefault();
      document.getElementById("formSuccess")?.classList.add("show");
    });
  }
});
