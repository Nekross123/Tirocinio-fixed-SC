use anchor_lang::prelude::*;

declare_id!("JDiaQThJ6C1erE6Cm47A22TXzVo976Bi5ggo77M9S9kX");

#[program]
pub mod simple_wallet {
    use super::*;

    pub fn deposit(ctx: Context<DepositOrWithdrawCtx>, amount_to_deposit: u64) -> Result<()> {
        require!(amount_to_deposit > 0, CustomError::InvalidAmount);

        let transfer_instruction = anchor_lang::solana_program::system_instruction::transfer(
            &ctx.accounts.owner.key(),
            &ctx.accounts.user_wallet_pda.key(),
            amount_to_deposit,
        );

        anchor_lang::solana_program::program::invoke(
            &transfer_instruction,
            &[
                ctx.accounts.owner.to_account_info(),
                ctx.accounts.user_wallet_pda.to_account_info(),
            ],
        )?;

        emit!(Deposit {
            sender: *ctx.accounts.owner.key,
            amount: amount_to_deposit,
            balance: **ctx.accounts.user_wallet_pda.to_account_info().lamports.borrow(),
        });

        Ok(())
    }

    pub fn create_transaction(
        ctx: Context<CreateTransactionCtx>,
        transaction_seed: String,
        transaction_lamports_amount: u64,
    ) -> Result<()> {
        require!(transaction_lamports_amount > 0, CustomError::InvalidAmount);

        let transaction_pda = &mut ctx.accounts.transaction_pda;
        let receiver = &ctx.accounts.receiver;

        transaction_pda.receiver = *receiver.key;
        transaction_pda.amount_in_lamports = transaction_lamports_amount;
        transaction_pda.executed = false;

        emit!(SubmitTransaction {
            owner: *ctx.accounts.owner.key,
            to: *receiver.key,
            value: transaction_lamports_amount,
        });

        Ok(())
    }

    pub fn execute_transaction(
        ctx: Context<ExecuteTransactionCtx>,
        transaction_seed: String,
    ) -> Result<()> {
        let user_wallet_pda = &mut ctx.accounts.user_wallet_pda;
        let transaction_pda = &mut ctx.accounts.transaction_pda;
        let receiver = &mut ctx.accounts.receiver;

        require!(
            !transaction_pda.executed,
            CustomError::TransactionAlreadyExecuted
        );

        transaction_pda.executed = true;

        **user_wallet_pda
            .to_account_info()
            .try_borrow_mut_lamports()? -= transaction_pda.amount_in_lamports;
        **receiver.try_borrow_mut_lamports()? += transaction_pda.amount_in_lamports;

        emit!(ExecuteTransaction {
            owner: *ctx.accounts.owner.key,
        });

        Ok(())
    }

    pub fn withdraw(ctx: Context<DepositOrWithdrawCtx>, amount_to_withdraw: u64) -> Result<()> {
        require!(amount_to_withdraw > 0, CustomError::InvalidAmount);

        let owner = &ctx.accounts.owner.to_account_info();
        let user_wallet_pda = &ctx.accounts.user_wallet_pda.to_account_info();

        **user_wallet_pda.try_borrow_mut_lamports()? -= amount_to_withdraw;
        **owner.try_borrow_mut_lamports()? += amount_to_withdraw;

        emit!(Withdraw {
            sender: *ctx.accounts.owner.key,
            amount: amount_to_withdraw,
            balance: **user_wallet_pda.lamports.borrow(),
        });

        Ok(())
    }
}

#[account]
#[derive(InitSpace)]
pub struct UserTransaction {
    pub receiver: Pubkey,
    pub amount_in_lamports: u64,
    pub executed: bool,
}

#[account]
#[derive(InitSpace)]
pub struct UserWallet {}

#[derive(Accounts)]
pub struct DepositOrWithdrawCtx<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(
        init_if_needed,
        payer = owner,
        seeds = ["wallet".as_ref(), owner.key().as_ref()],
        bump,
        space = 8 + UserWallet::INIT_SPACE
    )]
    pub user_wallet_pda: Account<'info, UserWallet>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(transaction_seed: String)]
pub struct CreateTransactionCtx<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(
        mut,
        seeds = ["wallet".as_ref(), owner.key().as_ref()],
        bump,
    )]
    pub user_wallet_pda: Account<'info, UserWallet>,
    #[account(
        init,
        payer = owner,
        space = 8 + UserTransaction::INIT_SPACE,
        seeds = [transaction_seed.as_ref(), user_wallet_pda.key().as_ref()],
        bump,
    )]
    pub transaction_pda: Account<'info, UserTransaction>,
    #[account(mut)]
    pub receiver: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(transaction_seed: String)]
pub struct ExecuteTransactionCtx<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(
        mut,
        seeds = ["wallet".as_ref(), owner.key().as_ref()],
        bump,
    )]
    pub user_wallet_pda: Account<'info, UserWallet>,
    #[account(
        mut,
        close = owner,
        seeds = [transaction_seed.as_ref(), user_wallet_pda.key().as_ref()],
        bump,
    )]
    pub transaction_pda: Account<'info, UserTransaction>,
    #[account(
        mut,
        constraint = transaction_pda.receiver == *receiver.key @ CustomError::InvalidReceiver
    )]
    pub receiver: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[error_code]
pub enum CustomError {
    #[msg("Invalid receiver")]
    InvalidReceiver,

    #[msg("Invalid amount, must be greater than 0")]
    InvalidAmount,

    #[msg("The provided transaction was already executed")]
    TransactionAlreadyExecuted,
}

#[event]
pub struct Deposit {
    sender: Pubkey,
    amount: u64,
    balance: u64,
}

#[event]
pub struct Withdraw {
    sender: Pubkey,
    amount: u64,
    balance: u64,
}

#[event]
pub struct SubmitTransaction {
    owner: Pubkey,
    to: Pubkey,
    value: u64,
}

#[event]
pub struct ExecuteTransaction {
    owner: Pubkey,
}
