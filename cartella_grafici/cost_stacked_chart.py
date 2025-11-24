import streamlit as st
import plotly.graph_objects as go

# ================================
# DATI ORIGINALI DEI COSTI (USD)
# ================================

auction_tezos_value     = [0.000269,0.004851,0.000332,0.000329]
auction_solana_value    = [0.2501,0.0007,0.0,0.0007]
auction_cardano_value   = [0.081,0.081,0.082,0.082]
auction_ethereum_value  = [0.161,0.128,0.062,0.097]

vesting_tezos_value     = [0.0,0.000330]
vesting_solana_value    = [0.2501,0.0014]
vesting_cardano_value   = [0.0,0.093]
vesting_ethereum_value  = [0.0,0.069]

simpletransfer_tezos_value    = [0.000197,0.000331]
simpletransfer_solana_value   = [0.2501,0.0007]
simpletransfer_cardano_value  = [0.076,0.076]
simpletransfer_ethereum_value = [0.055,0.077]

htlc_tezos_value       = [0.0,0.000395,0.000391]
htlc_solana_value      = [0.2501,0.0007,0.0014]
htlc_cardano_value     = [0.0,0.073,0.072]
htlc_ethereum_value    = [0.0,0.083,0.076]

bet_tezos_value        = [0.012874,0.004411,0.000332]
bet_solana_value       = [0.2501,0.0007,0.0007]
bet_cardano_value      = [0.108,0.106,0.106]
bet_ethereum_value     = [0.112,0.063,0.071]


# ================================
# ORGANIZZAZIONE PER CONTRATTO
# ================================

contracts = {
    "Auction": {
        "Tezos": auction_tezos_value,
        "Solana": auction_solana_value,
        "Ethereum": auction_ethereum_value,
        "Cardano": auction_cardano_value,
    },
    "Vesting": {
        "Tezos": vesting_tezos_value,
        "Solana": vesting_solana_value,
        "Ethereum": vesting_ethereum_value,
        "Cardano": vesting_cardano_value,
    },
    "SimpleTransfer": {
        "Tezos": simpletransfer_tezos_value,
        "Solana": simpletransfer_solana_value,
        "Ethereum": simpletransfer_ethereum_value,
        "Cardano": simpletransfer_cardano_value,
    },
    "HTLC": {
        "Tezos": htlc_tezos_value,
        "Solana": htlc_solana_value,
        "Ethereum": htlc_ethereum_value,
        "Cardano": htlc_cardano_value,
    },
    "Bet": {
        "Tezos": bet_tezos_value,
        "Solana": bet_solana_value,
        "Ethereum": bet_ethereum_value,
        "Cardano": bet_cardano_value,
    },
}

blockchains = ["Ethereum", "Solana", "Cardano", "Tezos"]


# ================================
# CALCOLO SOMME PER CONTRATTO/BLOCKCHAIN
# ================================

contract_totals = {name: [] for name in contracts}

for contract_name, data in contracts.items():
    for bc in blockchains:
        total = sum(data[bc])
        contract_totals[contract_name].append(total)


# ================================
# STREAMLIT + GRAFICI
# ================================

def main():
    st.title("Confronto dei Costi dei Contratti per Blockchain")

    # Colori per i contratti
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#9B59B6"]

    # ============ GRAFICO 1: COSTI TOTALI ============
    

    fig1 = go.Figure()

    for idx, contract_name in enumerate(contract_totals):
        fig1.add_trace(
            go.Bar(
                name=contract_name,
                x=blockchains,
                y=contract_totals[contract_name],
                marker_color=colors[idx % len(colors)],
            )
        )

    fig1.update_layout(
        barmode="stack",
        xaxis_title="Blockchain",
        yaxis_title="Costo (USD)",
        legend_title="Contratti",
        template="plotly_white",
        font=dict(color="black"),  # Tutti i testi in nero
        legend=dict(font=dict(color="black")),  # Titolo e voci legenda in nero
        legend_title_font=dict(color="black"),  # Titolo legenda in nero
    )
    
    # Imposta i colori degli assi in nero
    fig1.update_xaxes(tickfont=dict(color="black"), title_font=dict(color="black"))
    fig1.update_yaxes(tickfont=dict(color="black"), title_font=dict(color="black"))

    st.plotly_chart(fig1, use_container_width=True)

    # ============ GRAFICO 2: COSTI NORMALIZZATI (%) ============
#    st.subheader("Composizione Relativa dei Costi (%)")
#
#    totals = [
#        sum(contract_totals[c][i] for c in contract_totals)
#        for i in range(len(blockchains))
#    ]
#
#    normalized = {}
#
#    for c in contract_totals:
#        vals = contract_totals[c]
#        normalized[c] = [
#            (vals[i] / totals[i] * 100) if totals[i] > 0 else 0
#            for i in range(len(vals))
#        ]
#
#    fig2 = go.Figure()
#
#    for idx, contract_name in enumerate(normalized):
#        fig2.add_trace(
#            go.Bar(
#                name=contract_name,
#                x=blockchains,
#                y=normalized[contract_name],
#                marker_color=colors[idx % len(colors)],
#            )
#        )
#
#    fig2.update_layout(
#        barmode="stack",
#        xaxis_title="Blockchain",
#        yaxis_title="Percentuale (%)",
#        legend_title="Contratti",
#        template="plotly_white",
#    )
#
#    st.plotly_chart(fig2, use_container_width=True)


main()
