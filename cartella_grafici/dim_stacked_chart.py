import streamlit as st
import plotly.graph_objects as go


# ================================
# DATI ORIGINALI
# ================================

auction_tezos_value = [102,102,103,98]
auction_solana_value = [268,293,0,244]
auction_ethereum_value = [141,116,108,108]
auction_cardano_value = [4512,4518,4520,4524]

vesting_tezos_value = [0,102]
vesting_solana_value = [301,244]
vesting_ethereum_value = [0,108]
vesting_cardano_value = [0,3395]

simpletransfer_tezos_value = [96,103]
simpletransfer_solana_value = [287,351]
simpletransfer_ethereum_value = [116,140]
simpletransfer_cardano_value = [3609,3607]

htlc_tezos_value = [0,109,102]
htlc_solana_value = [325,252,310]
htlc_ethereum_value = [0,205,108]
htlc_cardano_value = [0,4021,4023]

bet_tezos_value = [179,142,103]
bet_solana_value = [392,313,279]
bet_ethereum_value = [108,140,108]
bet_cardano_value = [4903,4907,4911]


# ================================
# ORGANIZZAZIONE DATI PER CONTRATTO
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
# CALCOLO DELLE SOMME PER CONTRATTO/BLOCKCHAIN
# ================================

contract_totals = {name: [] for name in contracts}

for contract_name, data in contracts.items():
    for bc in blockchains:
        total = sum(data[bc])
        contract_totals[contract_name].append(total)


# ================================
# STREAMLIT
# ================================

def main():
    st.title("Confronto delle dimensioni dei Contratti per blockchain")

    # ============ GRAFICO 1: VALORI ASSOLUTI ============

   

    fig1 = go.Figure()

    for contract_name in contract_totals:
        fig1.add_trace(
            go.Bar(
                name=contract_name,
                x=blockchains,
                y=contract_totals[contract_name]
            )
        )

    fig1.update_layout(
        barmode="stack",
        xaxis_title="Blockchain",
        yaxis_title="Bytes",
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

    # ============ GRAFICO 2: NORMALIZZATO (%) ============
#
#    st.subheader("Composizione percentuale dei contratti (%)")
#
#    totals = [sum(contract_totals[c][i] for c in contract_totals) for i in range(len(blockchains))]
#    contract_totals_normalized = {}
#
#    for c in contract_totals:
#        vals = contract_totals[c]
#        contract_totals_normalized[c] = [
#            (vals[i] / totals[i] * 100) if totals[i] > 0 else 0
#            for i in range(len(vals))
#        ]
#
#    fig2 = go.Figure()
#
#    for contract_name in contract_totals_normalized:
#        fig2.add_trace(
#            go.Bar(
#                name=contract_name,
#                x=blockchains,
#                y=contract_totals_normalized[contract_name]
#            )
#        )
#
#    fig2.update_layout(
#        barmode="stack",
#        xaxis_title="Blockchain",
#        yaxis_title="Percentuale (%)",
#        template="plotly_white",
#    )
#
#    st.plotly_chart(fig2, use_container_width=True)


main()
